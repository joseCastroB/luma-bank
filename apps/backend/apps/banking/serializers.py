"""Validación de entrada y formato de salida de la API bancaria."""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from rest_framework import serializers

from .models import Account, Transaction
from .receipts import mask
from .services import SUPPORTED_CURRENCIES, available_balance, current_savings_rate


class OpenAccountSerializer(serializers.Serializer):
    currency = serializers.ChoiceField(choices=SUPPORTED_CURRENCIES)


class _AmountSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.01"), coerce_to_string=False
    )

    def validate_amount(self, value):
        if value > settings.TRANSFER_MAX_AMOUNT:
            raise serializers.ValidationError(
                f"El monto máximo por operación es {settings.TRANSFER_MAX_AMOUNT}."
            )
        return value


class OwnTransferSerializer(_AmountSerializer):
    source_number = serializers.CharField(max_length=20)
    destination_number = serializers.CharField(max_length=20)
    concept = serializers.CharField(max_length=140, required=False, allow_blank=True, default="")


class ThirdPartyTransferSerializer(_AmountSerializer):
    source_number = serializers.CharField(max_length=20)
    destination_cci = serializers.RegexField(
        r"^\d{20}$",
        error_messages={"invalid": "El CCI debe tener exactamente 20 dígitos."},
    )
    concept = serializers.CharField(max_length=140, required=False, allow_blank=True, default="")
    holder = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    bank = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    totp = serializers.CharField(max_length=6, required=False, allow_blank=True, default="")

    def validate_destination_cci(self, value):
        return value.strip()


class ExchangeQuoteSerializer(_AmountSerializer):
    from_currency = serializers.ChoiceField(choices=SUPPORTED_CURRENCIES)
    to_currency = serializers.ChoiceField(choices=SUPPORTED_CURRENCIES)


class HistoryFilterSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        start, end = attrs.get("date_from"), attrs.get("date_to")
        if start and end and start > end:
            raise serializers.ValidationError("La fecha inicial no puede ser mayor que la final.")
        return attrs


def _rate_payload(currency: str) -> dict | None:
    rate = current_savings_rate(currency)
    if rate is None:
        return None
    return {"currency": currency, "trea": str(rate.trea), "valid_from": rate.valid_from}


def savings_rates() -> list[dict]:
    payloads = (_rate_payload(currency) for currency in SUPPORTED_CURRENCIES)
    return [payload for payload in payloads if payload]


def account_payload(account: Account) -> dict:
    return {
        "number": account.number,
        "kind": account.kind,
        "kind_label": account.get_kind_display(),
        "currency": account.currency,
        "status": account.status,
        "status_label": account.get_status_display(),
        "balance": f"{account.balance:.2f}",
        "available_balance": f"{available_balance(account):.2f}",
        "accrued_interest": f"{account.accrued_interest:.2f}",
        "opened_at": account.opened_at,
        "savings_rate": _rate_payload(account.currency),
    }


def transaction_for_account(tx: Transaction, account: Account) -> dict:
    """Una operación vista desde una de sus cuentas: cargo u abono, nunca ambos."""
    is_debit = tx.source_account_id == account.pk
    if is_debit:
        amount, currency, balance_after = tx.amount + tx.fee, tx.currency, tx.source_balance_after
        counterpart = (
            tx.destination_account.number
            if tx.destination_account_id
            else tx.external_destination_number
        )
    else:
        amount = tx.destination_amount or tx.amount
        currency = tx.destination_currency or tx.currency
        balance_after = tx.destination_balance_after
        counterpart = tx.source_account.number if tx.source_account_id else None
    return {
        "operation_code": tx.operation_code,
        "kind": tx.kind,
        "kind_label": tx.get_kind_display(),
        "direction": "debit" if is_debit else "credit",
        "amount": str(amount),
        "currency": currency,
        "balance_after": str(balance_after) if balance_after is not None else None,
        "counterpart": mask(counterpart) if counterpart else None,
        "concept": tx.concept,
        "status": tx.status,
        "exchange_rate": str(tx.exchange_rate) if tx.exchange_rate else None,
        "created_at": tx.created_at,
        "has_receipt": is_debit,
    }


def operation_payload(tx: Transaction) -> dict:
    """Resultado que recibe quien ordenó la operación."""
    return {
        "operation_code": tx.operation_code,
        "kind": tx.kind,
        "kind_label": tx.get_kind_display(),
        "status": tx.status,
        "amount": str(tx.amount),
        "fee": str(tx.fee),
        "currency": tx.currency,
        "exchange_rate": str(tx.exchange_rate) if tx.exchange_rate else None,
        "destination_amount": str(tx.destination_amount) if tx.destination_amount else None,
        "destination_currency": tx.destination_currency,
        "source_balance_after": str(tx.source_balance_after),
        "destination_balance_after": (
            str(tx.destination_balance_after) if tx.destination_balance_after is not None else None
        ),
        "completed_at": tx.completed_at,
    }
