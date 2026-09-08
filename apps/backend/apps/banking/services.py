"""Servicios del dominio bancario."""

from __future__ import annotations

import secrets

from .models import Account

# Código de entidad + oficina (ficticios para el proyecto).
_BANK_CODE = "011"
_BRANCH_CODE = "0021"


def _luhn_check_digit(number: str) -> str:
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10)


def generate_account_number() -> str:
    """Número de 20 dígitos: entidad(3) + oficina(4) + serial(12) + control(1)."""
    for _ in range(10):
        serial = "".join(secrets.choice("0123456789") for _ in range(12))
        body = f"{_BANK_CODE}{_BRANCH_CODE}{serial}"
        number = body + _luhn_check_digit(body)
        if not Account.objects.filter(number=number).exists():
            return number
    raise RuntimeError("No se pudo generar un número de cuenta único.")


def open_account(user, *, currency: str = "PEN") -> Account:
    return Account.objects.create(
        user=user,
        number=generate_account_number(),
        currency=currency,
    )
