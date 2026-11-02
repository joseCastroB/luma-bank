"""Devenga el interés diario y capitaliza a fin de mes. Se puede correr varias veces."""

from datetime import date

from django.core.management.base import BaseCommand

from apps.banking.interest import accrue_all


class Command(BaseCommand):
    help = "Devenga intereses de las cuentas de ahorro hasta ayer (o hasta --hasta)."

    def add_arguments(self, parser):
        parser.add_argument("--hasta", type=date.fromisoformat, help="Último día, AAAA-MM-DD.")

    def handle(self, *args, **options):
        updated = accrue_all(until=options["hasta"])
        self.stdout.write(f"Cuentas actualizadas: {updated}")
