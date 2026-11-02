"""Apertura de cuenta, saldo y TREA, historial de movimientos."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog
from apps.banking.models import Account, SavingsRate, Transaction
from apps.banking.services import open_account, settle


def _detalle(numero):
    return reverse("banking:account-detail", args=[numero])


def _historial(numero):
    return reverse("banking:account-transactions", args=[numero])


@pytest.mark.django_db
class TestAperturaDeCuenta:
    def test_crea_cuenta_con_saldo_cero_y_trea_visible(self, api, cliente, tasas):
        resp = api.post(reverse("banking:accounts"), {"currency": "PEN"}, format="json")
        assert resp.status_code == 201
        body = resp.json()
        assert body["balance"] == "0.00"
        assert body["kind"] == "savings"
        assert body["savings_rate"]["trea"] == "4.00"
        assert len(body["number"]) == 20
        assert AuditLog.objects.filter(user=cliente, action="account.open").exists()

    def test_permite_cuenta_en_dolares(self, api, tasas):
        resp = api.post(reverse("banking:accounts"), {"currency": "USD"}, format="json")
        assert resp.status_code == 201
        assert resp.json()["currency"] == "USD"

    def test_rechaza_moneda_no_disponible(self, api, tasas):
        resp = api.post(reverse("banking:accounts"), {"currency": "EUR"}, format="json")
        assert resp.status_code == 400

    def test_respeta_el_maximo_por_moneda(self, api, tasas, settings):
        settings.MAX_ACCOUNTS_PER_CURRENCY = 1
        url = reverse("banking:accounts")
        assert api.post(url, {"currency": "PEN"}, format="json").status_code == 201
        resp = api.post(url, {"currency": "PEN"}, format="json")
        assert resp.status_code == 409
        assert resp.json()["code"] == "too_many_accounts"

    def test_exige_identidad_verificada(self, api, cliente, tasas):
        cliente.is_identity_verified = False
        cliente.save()
        resp = api.post(reverse("banking:accounts"), {"currency": "PEN"}, format="json")
        assert resp.status_code == 403
        assert resp.json()["code"] == "identity_not_verified"

    def test_requiere_autenticacion(self, db):
        assert APIClient().get(reverse("banking:accounts")).status_code == 401


@pytest.mark.django_db
class TestSaldoYTrea:
    def test_muestra_saldo_contable_y_disponible(self, api, cuenta_pen, tasas):
        body = api.get(_detalle(cuenta_pen.number)).json()
        assert body["balance"] == "1000.00"
        assert body["available_balance"] == "1000.00"

    def test_disponible_descuenta_operaciones_pendientes(self, api, cuenta_pen, tasas):
        Transaction.objects.create(
            operation_code="PEND-1",
            kind=Transaction.Kind.INTERBANK_TRANSFER,
            source_account=cuenta_pen,
            amount=Decimal("100.00"),
            fee=Decimal("5.00"),
            status=Transaction.Status.PENDING,
        )
        body = api.get(_detalle(cuenta_pen.number)).json()
        assert body["balance"] == "1000.00"
        assert body["available_balance"] == "895.00"

    def test_trea_mas_reciente_con_su_vigencia(self, api, cuenta_pen, tasas):
        hoy = timezone.localdate()
        SavingsRate.objects.create(currency="PEN", trea=Decimal("4.50"), valid_from=hoy)
        rate = api.get(_detalle(cuenta_pen.number)).json()["savings_rate"]
        assert rate["trea"] == "4.50"
        assert rate["valid_from"] == hoy.isoformat()

    def test_ignora_una_trea_futura(self, api, cuenta_pen, tasas):
        manana = timezone.localdate() + timedelta(days=1)
        SavingsRate.objects.create(currency="PEN", trea=Decimal("9.00"), valid_from=manana)
        assert api.get(_detalle(cuenta_pen.number)).json()["savings_rate"]["trea"] == "4.00"

    def test_no_ve_cuentas_ajenas(self, api, cuenta_ajena):
        assert api.get(_detalle(cuenta_ajena.number)).status_code == 404
        assert api.get(_historial(cuenta_ajena.number)).status_code == 404

    def test_lista_tasas_aunque_no_tenga_cuentas(self, api, tasas):
        body = api.get(reverse("banking:accounts")).json()
        assert body["accounts"] == []
        assert {r["currency"] for r in body["savings_rates"]} == {"PEN", "USD"}


def _deposito(cuenta, monto="10.00"):
    return settle(kind=Transaction.Kind.DEPOSIT, amount=Decimal(monto), destination=cuenta)


@pytest.mark.django_db
class TestHistorial:
    def test_cargos_y_abonos_desde_cada_cuenta(self, api, cuenta_pen, cuenta_pen_2):
        settle(
            kind=Transaction.Kind.OWN_TRANSFER,
            amount=Decimal("100.00"),
            source=cuenta_pen,
            destination=cuenta_pen_2,
        )
        cargo = api.get(_historial(cuenta_pen.number)).json()["results"][0]
        abono = api.get(_historial(cuenta_pen_2.number)).json()["results"][0]

        assert cargo["direction"] == "debit"
        assert cargo["balance_after"] == "900.00"
        assert cargo["has_receipt"] is True
        assert abono["direction"] == "credit"
        assert abono["balance_after"] == "100.00"
        assert abono["has_receipt"] is False

    def test_filtra_por_rango_de_fechas(self, api, cuenta_pen):
        viejo = _deposito(cuenta_pen)
        Transaction.objects.filter(pk=viejo.pk).update(
            created_at=timezone.make_aware(timezone.datetime(2026, 3, 15, 12))
        )
        reciente = _deposito(cuenta_pen)

        resp = api.get(
            _historial(cuenta_pen.number), {"date_from": "2026-03-01", "date_to": "2026-03-31"}
        )
        assert [t["operation_code"] for t in resp.json()["results"]] == [viejo.operation_code]

        resp = api.get(_historial(cuenta_pen.number), {"date_from": timezone.localdate()})
        assert [t["operation_code"] for t in resp.json()["results"]] == [reciente.operation_code]

    def test_rechaza_un_rango_invertido(self, api, cuenta_pen):
        resp = api.get(
            _historial(cuenta_pen.number), {"date_from": "2026-03-31", "date_to": "2026-03-01"}
        )
        assert resp.status_code == 400

    def test_rechaza_una_fecha_invalida(self, api, cuenta_pen):
        resp = api.get(_historial(cuenta_pen.number), {"date_from": "ayer"})
        assert resp.status_code == 400

    def test_pagina_un_historial_extenso(self, api, cuenta_pen):
        for _ in range(25):
            _deposito(cuenta_pen)
        primera = api.get(_historial(cuenta_pen.number)).json()
        assert primera["count"] == 25
        assert len(primera["results"]) == 20
        assert primera["next"]
        segunda = api.get(_historial(cuenta_pen.number), {"page": 2}).json()
        assert len(segunda["results"]) == 5

    def test_oculta_el_numero_de_la_contraparte(self, api, cuenta_pen, cuenta_ajena):
        settle(
            kind=Transaction.Kind.THIRD_PARTY_TRANSFER,
            amount=Decimal("5.00"),
            source=cuenta_pen,
            destination=cuenta_ajena,
        )
        fila = api.get(_historial(cuenta_pen.number)).json()["results"][0]
        assert fila["counterpart"] == f"****{cuenta_ajena.number[-4:]}"


@pytest.mark.django_db
class TestSemillaDeTasas:
    def test_la_migracion_publica_una_trea_por_moneda(self):
        assert SavingsRate.objects.filter(currency="PEN").exists()
        assert SavingsRate.objects.filter(currency="USD").exists()

    def test_las_cuentas_nuevas_son_de_ahorros(self, cliente):
        assert open_account(cliente).kind == Account.Kind.SAVINGS
