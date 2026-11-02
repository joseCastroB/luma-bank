"""Abona saldo a una cuenta para pruebas y demos. Solo con DEBUG activo."""

from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.banking.models import Account, Transaction
from apps.banking.services import settle


class Command(BaseCommand):
    help = "Deposita un monto en una cuenta (solo en desarrollo)."

    def add_arguments(self, parser):
        parser.add_argument("numero", help="Número de cuenta.")
        parser.add_argument("monto", type=Decimal)

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Este comando solo funciona en desarrollo.")
        if options["monto"] <= 0:
            raise CommandError("El monto debe ser mayor que cero.")

        with transaction.atomic():
            account = Account.objects.select_for_update().filter(number=options["numero"]).first()
            if account is None:
                raise CommandError("No existe esa cuenta.")
            settle(
                kind=Transaction.Kind.DEPOSIT,
                amount=options["monto"],
                destination=account,
                concept="Depósito de prueba",
            )
        self.stdout.write(f"Nuevo saldo: {account.currency} {account.balance}")
