"""Modelo v3: reglas de la tabla `transaccion`."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.banking.models import Transaction
from apps.banking.services import open_account

User = get_user_model()


@pytest.fixture
def cuenta(db):
    user = User.objects.create_user(username="a@example.com", email="a@example.com", password="x")
    return open_account(user)


def _transaccion(**overrides):
    data = {
        "operation_code": "OP-1",
        "kind": Transaction.Kind.DEPOSIT,
        "amount": Decimal("10.00"),
    }
    data.update(overrides)
    return Transaction.objects.create(**data)


@pytest.mark.django_db
class TestReglasDeTransaccion:
    def test_abono_solo_con_cuenta_destino(self, cuenta):
        assert _transaccion(destination_account=cuenta).source_account is None

    def test_interbancaria_sin_cuenta_destino(self, cuenta):
        operacion = _transaccion(
            kind=Transaction.Kind.INTERBANK_TRANSFER,
            source_account=cuenta,
            external_destination_number="00212345678901234567",
            external_destination_holder="Ana Pérez",
            external_destination_bank="Otro Banco",
        )
        assert operacion.destination_account is None

    @pytest.mark.parametrize(
        ("overrides", "restriccion"),
        [
            ({"amount": Decimal("0")}, "transaccion_monto_gt_0"),
            ({"fee": Decimal("-1")}, "transaccion_comision_gte_0"),
        ],
    )
    def test_montos_invalidos(self, cuenta, overrides, restriccion):
        with pytest.raises(IntegrityError, match=restriccion), transaction.atomic():
            _transaccion(destination_account=cuenta, **overrides)

    def test_requiere_alguna_cuenta(self, db):
        with pytest.raises(IntegrityError, match="transaccion_con_alguna_cuenta"):
            with transaction.atomic():
                _transaccion()

    def test_origen_y_destino_deben_ser_distintos(self, cuenta):
        with pytest.raises(IntegrityError, match="transaccion_cuentas_distintas"):
            with transaction.atomic():
                _transaccion(source_account=cuenta, destination_account=cuenta)

    def test_codigo_de_operacion_unico(self, cuenta):
        _transaccion(destination_account=cuenta)
        with pytest.raises(IntegrityError), transaction.atomic():
            _transaccion(destination_account=cuenta)
