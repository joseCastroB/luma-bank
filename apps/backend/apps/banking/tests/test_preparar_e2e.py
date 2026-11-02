"""El comando que prepara las pruebas E2E: repetible y limitado a desarrollo."""

import json
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from apps.accounts.services import auth
from apps.banking.models import Account, ExchangeRate, SavingsRate, Transaction
from apps.banking.services import open_account

User = get_user_model()

pytestmark = pytest.mark.django_db


def _preparar() -> dict:
    salida = StringIO()
    call_command("preparar_e2e", stdout=salida)
    return json.loads(salida.getvalue())


@pytest.fixture
def con_debug(settings):
    settings.DEBUG = True


def test_no_corre_sin_debug(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        _preparar()
    assert not User.objects.filter(email="e2e@lumabank.test").exists()


def test_deja_cuentas_y_tasas_listas(con_debug):
    numeros = _preparar()

    pen = Account.objects.get(number=numeros["cuentaPen"])
    assert pen.balance == Decimal("5000.00")
    assert Transaction.objects.filter(destination_account=pen).count() == 25
    assert Account.objects.get(number=numeros["cuentaUsd"]).currency == "USD"
    assert SavingsRate.objects.filter(currency="USD").exists()
    assert ExchangeRate.objects.exists()


def test_el_cliente_bloqueado_queda_bloqueado(con_debug):
    _preparar()
    assert auth.is_locked(User.objects.get(email="e2e.bloqueado@lumabank.test"))
    assert not auth.is_locked(User.objects.get(email="e2e@lumabank.test"))


def test_repetirlo_reinicia_solo_a_los_clientes_de_prueba(con_debug, cuenta_ajena):
    primera = _preparar()
    # Una cuenta extra, como la que abren las pruebas, no sobrevive a la siguiente corrida.
    open_account(User.objects.get(email="e2e@lumabank.test"))

    segunda = _preparar()

    assert primera != segunda
    assert Account.objects.filter(user__email="e2e@lumabank.test").count() == 3
    assert Account.objects.filter(pk=cuenta_ajena.pk).exists()
