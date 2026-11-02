"""
Intereses de las cuentas de ahorro: devengo diario y capitalización mensual.

La tasa diaria sale de la TREA: (1 + TREA) ^ (1/365) - 1. Cada día procesado queda
marcado en la cuenta, así que correr el proceso varias veces no duplica intereses y
si deja de correr unos días, se pone al día con el saldo que la cuenta tenga entonces.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import ROUND_DOWN, Decimal

from django.db import transaction
from django.utils import timezone

from .models import Account, SavingsRate, Transaction
from .services import CENT, settle

_MICRO = Decimal("0.000001")


def daily_rate(trea: Decimal) -> Decimal:
    return (1 + trea / 100) ** (Decimal(1) / Decimal(365)) - 1


def _rate_on(currency: str, day: date) -> SavingsRate | None:
    return (
        SavingsRate.objects.filter(currency=currency, valid_from__lte=day)
        .order_by("-valid_from")
        .first()
    )


def _is_month_end(day: date) -> bool:
    return day.day == calendar.monthrange(day.year, day.month)[1]


def _capitalize(account: Account, day: date) -> Transaction | None:
    amount = account.accrued_interest.quantize(CENT, rounding=ROUND_DOWN)
    if amount <= 0:
        return None
    account.accrued_interest -= amount
    return settle(
        kind=Transaction.Kind.INTEREST,
        amount=amount,
        destination=account,
        concept=f"Intereses de {day:%m/%Y}",
    )


def accrue_account(account_pk: int, *, until: date) -> int:
    """Devenga los días pendientes de una cuenta hasta `until`. Devuelve los días procesados."""
    with transaction.atomic():
        account = Account.objects.select_for_update().get(pk=account_pk)
        if account.status != Account.Status.ACTIVE:
            return 0

        day = (
            account.last_accrual_on + timedelta(days=1)
            if account.last_accrual_on
            else timezone.localdate(account.opened_at)
        )
        processed = 0
        while day <= until:
            rate = _rate_on(account.currency, day)
            if rate is not None:
                interest = account.balance * daily_rate(rate.trea)
                account.accrued_interest += interest.quantize(_MICRO, rounding=ROUND_DOWN)
            if _is_month_end(day):
                _capitalize(account, day)
            account.last_accrual_on = day
            processed += 1
            day += timedelta(days=1)

        if processed:
            account.save(update_fields=["accrued_interest", "last_accrual_on"])
        return processed


def accrue_all(*, until: date | None = None) -> int:
    """Procesa todas las cuentas activas hasta ayer (el día de hoy aún no termina)."""
    until = until or timezone.localdate() - timedelta(days=1)
    accounts = Account.objects.filter(
        status=Account.Status.ACTIVE, kind=Account.Kind.SAVINGS
    ).values_list("pk", flat=True)
    return sum(1 for pk in accounts if accrue_account(pk, until=until))
