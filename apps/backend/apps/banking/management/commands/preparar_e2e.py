"""Deja los clientes de las pruebas E2E en un estado conocido. Solo con DEBUG activo."""

import json
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.services import crypto
from apps.banking.models import Account, ExchangeRate, SavingsRate, Transaction
from apps.banking.services import current_savings_rate, open_account, settle

User = get_user_model()

# Valores de prueba, repetidos en apps/frontend/e2e/datos.ts.
CLAVE = "E2e-Clave-Segura-2026"  # noqa: S105
SECRETO_TOTP = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"  # noqa: S105
CLIENTES = {
    "e2e@lumabank.test": "90000001",
    "e2e.destino@lumabank.test": "90000002",
    "e2e.bloqueado@lumabank.test": "90000003",
}
# Más de 20 movimientos para que el historial tenga una segunda página.
DEPOSITOS = 25
MONTO_DEPOSITO = Decimal("200.00")
SALDO_USD = Decimal("500.00")


class Command(BaseCommand):
    help = "Prepara clientes, cuentas y tasas para las pruebas E2E (solo en desarrollo)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Este comando solo funciona en desarrollo.")

        with transaction.atomic():
            cuentas = Account.objects.filter(user__email__in=CLIENTES)
            Transaction.objects.filter(
                Q(source_account__in=cuentas) | Q(destination_account__in=cuentas)
            ).delete()
            cuentas.delete()

            cliente = _cliente("e2e@lumabank.test")
            destino = _cliente("e2e.destino@lumabank.test")
            bloqueado = _cliente("e2e.bloqueado@lumabank.test")
            bloqueado.locked_until = timezone.now() + timedelta(hours=1)
            bloqueado.save(update_fields=["locked_until"])

            _publicar_tasas()

            pen = open_account(cliente)
            pen_2 = open_account(cliente)
            usd = open_account(cliente, currency="USD")
            for _ in range(DEPOSITOS):
                settle(
                    kind=Transaction.Kind.DEPOSIT,
                    amount=MONTO_DEPOSITO,
                    destination=pen,
                    concept="Depósito de prueba",
                )
            settle(
                kind=Transaction.Kind.DEPOSIT,
                amount=SALDO_USD,
                destination=usd,
                concept="Depósito de prueba",
            )
            ajena = open_account(destino)

        self.stdout.write(
            json.dumps(
                {
                    "cuentaPen": pen.number,
                    "cuentaPen2": pen_2.number,
                    "cuentaUsd": usd.number,
                    "cuentaDestino": ajena.number,
                }
            )
        )


def _cliente(correo: str) -> User:
    cliente, _ = User.objects.get_or_create(
        email=correo, defaults={"username": correo, "dni": CLIENTES[correo]}
    )
    cliente.first_name = "Prueba"
    cliente.last_name = "E2E"
    cliente.is_identity_verified = True
    cliente.totp_secret_encrypted = crypto.encrypt_secret(SECRETO_TOTP)
    cliente.failed_login_attempts = 0
    cliente.failed_facial_attempts = 0
    cliente.locked_until = None
    cliente.set_password(CLAVE)
    cliente.save()
    return cliente


def _publicar_tasas() -> None:
    """Sin esto, una base nueva dependería de que SUNAT responda durante la prueba."""
    hoy = timezone.localdate()
    for moneda, trea in (("PEN", Decimal("4.00")), ("USD", Decimal("1.00"))):
        if current_savings_rate(moneda) is None:
            SavingsRate.objects.create(currency=moneda, trea=trea, valid_from=hoy)
    limite = hoy - timedelta(days=settings.EXCHANGE_RATE_MAX_AGE_DAYS)
    if not ExchangeRate.objects.filter(date__gte=limite).exists():
        ExchangeRate.objects.create(
            date=hoy, buy=Decimal("3.4000"), sell=Decimal("3.5000"), source="E2E"
        )
