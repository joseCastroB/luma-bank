"""Fixtures de la API bancaria."""

from datetime import date
from decimal import Decimal

import pyotp
import pytest
import requests
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.services import crypto
from apps.banking.models import Account, ExchangeRate, SavingsRate
from apps.banking.services import open_account

User = get_user_model()

TOTP_SECRET = pyotp.random_base32()


@pytest.fixture(autouse=True)
def _sin_red(monkeypatch):
    """Ninguna prueba consulta a SUNAT de verdad."""

    def _fail(*args, **kwargs):
        raise requests.ConnectionError("Sin red en las pruebas")

    monkeypatch.setattr(requests, "get", _fail)


@pytest.fixture
def cliente(db):
    return User.objects.create_user(
        username="ana@example.com",
        email="ana@example.com",
        password="Clave-Segura-2026",
        first_name="Ana",
        last_name="Pérez",
        is_identity_verified=True,
        totp_secret_encrypted=crypto.encrypt_secret(TOTP_SECRET),
    )


@pytest.fixture
def otro_cliente(db):
    return User.objects.create_user(
        username="beto@example.com",
        email="beto@example.com",
        password="Clave-Segura-2026",
        is_identity_verified=True,
    )


@pytest.fixture
def api(cliente):
    client = APIClient()
    client.force_authenticate(cliente)
    return client


@pytest.fixture
def tasas(db):
    SavingsRate.objects.all().delete()
    SavingsRate.objects.create(currency="PEN", trea=Decimal("4.00"), valid_from=date(2026, 1, 1))
    SavingsRate.objects.create(currency="USD", trea=Decimal("1.00"), valid_from=date(2026, 1, 1))


@pytest.fixture
def tipo_cambio(db):
    return ExchangeRate.objects.create(
        date=timezone.localdate(), buy=Decimal("3.4000"), sell=Decimal("3.5000")
    )


def con_saldo(account: Account, saldo: str) -> Account:
    account.balance = Decimal(saldo)
    account.save(update_fields=["balance"])
    return account


@pytest.fixture
def cuenta_pen(cliente):
    return con_saldo(open_account(cliente), "1000.00")


@pytest.fixture
def cuenta_pen_2(cliente):
    return open_account(cliente)


@pytest.fixture
def cuenta_usd(cliente):
    return con_saldo(open_account(cliente, currency="USD"), "100.00")


@pytest.fixture
def cuenta_ajena(otro_cliente):
    return open_account(otro_cliente)


@pytest.fixture
def codigo_totp():
    return pyotp.TOTP(TOTP_SECRET).now()
