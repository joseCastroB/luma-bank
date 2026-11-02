"""API bancaria: cuentas, historial, transferencias y conversión de moneda."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv46_address
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import AuditLog

from . import exchange_rates, receipts, serializers, services
from .models import Account, Transaction


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    try:
        validate_ipv46_address(ip)
    except ValidationError:
        return None
    return ip


def _audit(request, action: str, *, entity: str, entity_id: str, **metadata) -> None:
    AuditLog.objects.create(
        user=request.user,
        action=action,
        entity=entity,
        entity_id=entity_id,
        ip_address=_client_ip(request),
        metadata=metadata,
    )


def _audit_operation(request, action: str, tx: Transaction) -> None:
    _audit(
        request,
        action,
        entity="transaccion",
        entity_id=tx.operation_code,
        kind=tx.kind,
        amount=str(tx.amount),
        currency=tx.currency,
    )


class BankingView(APIView):
    def handle_exception(self, exc):
        if isinstance(exc, services.BankingError):
            return Response(
                {"detail": exc.message, "code": exc.code, **exc.extra}, status=exc.status
            )
        return super().handle_exception(exc)


class TransferView(BankingView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "transfer"


class HistoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AccountsView(BankingView):
    def get(self, request):
        accounts = request.user.accounts.order_by("opened_at")
        return Response(
            {
                "accounts": [serializers.account_payload(a) for a in accounts],
                "savings_rates": serializers.savings_rates(),
            }
        )

    def post(self, request):
        serializer = serializers.OpenAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = services.open_savings_account(
            request.user, currency=serializer.validated_data["currency"]
        )
        _audit(
            request,
            "account.open",
            entity="cuenta",
            entity_id=str(account.pk),
            currency=account.currency,
        )
        return Response(serializers.account_payload(account), status=status.HTTP_201_CREATED)


class AccountDetailView(BankingView):
    def get(self, request, number):
        account = get_object_or_404(Account, user=request.user, number=number)
        return Response(serializers.account_payload(account))


class AccountTransactionsView(BankingView):
    def get(self, request, number):
        account = get_object_or_404(Account, user=request.user, number=number)
        filters = serializers.HistoryFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)

        transactions = (
            Transaction.objects.filter(Q(source_account=account) | Q(destination_account=account))
            .select_related("source_account", "destination_account")
            .order_by("-created_at", "-pk")
        )
        if start := filters.validated_data.get("date_from"):
            transactions = transactions.filter(created_at__date__gte=start)
        if end := filters.validated_data.get("date_to"):
            transactions = transactions.filter(created_at__date__lte=end)

        paginator = HistoryPagination()
        page = paginator.paginate_queryset(transactions, request, view=self)
        return paginator.get_paginated_response(
            [serializers.transaction_for_account(tx, account) for tx in page]
        )


class OwnTransferView(TransferView):
    def post(self, request):
        serializer = serializers.OwnTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tx = services.transfer_between_own_accounts(request.user, **serializer.validated_data)
        _audit_operation(request, "transfer.own", tx)
        return Response(serializers.operation_payload(tx), status=status.HTTP_201_CREATED)


class ThirdPartyTransferView(TransferView):
    def post(self, request):
        serializer = serializers.ThirdPartyTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tx = services.transfer_to_third_party(request.user, **serializer.validated_data)
        _audit_operation(request, "transfer.third_party", tx)
        return Response(serializers.operation_payload(tx), status=status.HTTP_201_CREATED)


class ExchangeQuoteView(BankingView):
    def get(self, request):
        serializer = serializers.ExchangeQuoteSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            rate = exchange_rates.current_rate()
        except exchange_rates.ExchangeRateUnavailable:
            return Response(
                {
                    "detail": "El tipo de cambio oficial no está disponible. Inténtalo más tarde.",
                    "code": "exchange_rate_unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        credited, applied = services.quote(
            data["amount"],
            from_currency=data["from_currency"],
            to_currency=data["to_currency"],
            rate=rate,
        )
        return Response(
            {
                "amount": str(data["amount"]),
                "from_currency": data["from_currency"],
                "to_currency": data["to_currency"],
                "credited": str(credited),
                "applied_rate": str(applied),
                "buy": str(rate.buy),
                "sell": str(rate.sell),
                "date": rate.date,
                "source": rate.source,
            }
        )


class ExchangeView(TransferView):
    def post(self, request):
        serializer = serializers.OwnTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        source = get_object_or_404(Account, user=request.user, number=data["source_number"])
        destination = get_object_or_404(
            Account, user=request.user, number=data["destination_number"]
        )
        if source.currency == destination.currency:
            raise services.BankingError(
                "Las dos cuentas están en la misma moneda: usa una transferencia.",
                code="same_currency",
            )
        tx = services.transfer_between_own_accounts(request.user, **data)
        _audit_operation(request, "exchange.convert", tx)
        return Response(serializers.operation_payload(tx), status=status.HTTP_201_CREATED)


class ReceiptView(BankingView):
    """Solo quien ordenó la operación descarga su comprobante."""

    def get(self, request, code):
        tx = get_object_or_404(
            Transaction.objects.select_related("source_account", "destination_account"),
            operation_code=code,
            source_account__user=request.user,
        )
        response = HttpResponse(receipts.render_receipt(tx), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="comprobante-{code}.pdf"'
        return response
