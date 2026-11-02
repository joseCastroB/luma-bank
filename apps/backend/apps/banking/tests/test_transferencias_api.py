"""Transferencias propias, a terceros por CCI y conversión de moneda."""

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog
from apps.banking.models import Account, Transaction
from apps.banking.receipts import _rows

CCI_EXTERNO = "00219300123456789012"


def _propia(api, origen, destino, monto="100.00", **extra):
    return api.post(
        reverse("banking:transfer-own"),
        {
            "source_number": origen.number,
            "destination_number": destino.number,
            "amount": monto,
            **extra,
        },
        format="json",
    )


def _tercero(api, origen, cci=CCI_EXTERNO, monto="100.00", **extra):
    return api.post(
        reverse("banking:transfer-third-party"),
        {
            "source_number": origen.number,
            "destination_cci": cci,
            "amount": monto,
            "holder": "Carla Ríos",
            "bank": "Otro Banco",
            **extra,
        },
        format="json",
    )


def _saldo(cuenta):
    return Account.objects.get(pk=cuenta.pk).balance


@pytest.mark.django_db
class TestTransferenciaPropia:
    def test_debito_y_credito_suman_cero(self, api, cliente, cuenta_pen, cuenta_pen_2):
        resp = _propia(api, cuenta_pen, cuenta_pen_2, concept="Ahorro")
        assert resp.status_code == 201, resp.content
        assert _saldo(cuenta_pen) == Decimal("900.00")
        assert _saldo(cuenta_pen_2) == Decimal("100.00")

        tx = Transaction.objects.get()
        assert tx.kind == Transaction.Kind.OWN_TRANSFER
        assert tx.status == Transaction.Status.COMPLETED
        assert tx.source_balance_after == Decimal("900.00")
        assert tx.destination_balance_after == Decimal("100.00")
        assert tx.completed_at is not None
        assert len(tx.operation_code) == 20
        assert AuditLog.objects.filter(user=cliente, action="transfer.own").count() == 1

    def test_saldo_insuficiente_no_mueve_dinero(self, api, cuenta_pen, cuenta_pen_2):
        resp = _propia(api, cuenta_pen, cuenta_pen_2, monto="1000.01")
        assert resp.status_code == 409
        assert resp.json()["code"] == "insufficient_funds"
        assert "insuficiente" in resp.json()["detail"].lower()
        assert _saldo(cuenta_pen) == Decimal("1000.00")
        assert _saldo(cuenta_pen_2) == Decimal("0.00")
        assert not Transaction.objects.exists()

    def test_puede_transferir_todo_el_saldo(self, api, cuenta_pen, cuenta_pen_2):
        assert _propia(api, cuenta_pen, cuenta_pen_2, monto="1000.00").status_code == 201
        assert _saldo(cuenta_pen) == Decimal("0.00")

    def test_rechaza_la_misma_cuenta(self, api, cuenta_pen):
        resp = _propia(api, cuenta_pen, cuenta_pen)
        assert resp.status_code == 400
        assert resp.json()["code"] == "same_account"

    def test_no_puede_usar_una_cuenta_ajena_como_origen(self, api, cuenta_pen, cuenta_ajena):
        resp = _propia(api, cuenta_ajena, cuenta_pen)
        assert resp.status_code == 404
        assert _saldo(cuenta_ajena) == Decimal("0.00")

    def test_no_puede_usar_una_cuenta_ajena_como_destino(self, api, cuenta_pen, cuenta_ajena):
        assert _propia(api, cuenta_pen, cuenta_ajena).status_code == 404
        assert _saldo(cuenta_pen) == Decimal("1000.00")

    def test_rechaza_cuenta_congelada(self, api, cuenta_pen, cuenta_pen_2):
        Account.objects.filter(pk=cuenta_pen_2.pk).update(status=Account.Status.FROZEN)
        resp = _propia(api, cuenta_pen, cuenta_pen_2)
        assert resp.status_code == 409
        assert resp.json()["code"] == "account_inactive"
        assert _saldo(cuenta_pen) == Decimal("1000.00")

    @pytest.mark.parametrize("monto", ["0", "-5", "0.001", "abc", "100000.01"])
    def test_rechaza_montos_invalidos(self, api, cuenta_pen, cuenta_pen_2, monto):
        assert _propia(api, cuenta_pen, cuenta_pen_2, monto=monto).status_code == 400
        assert _saldo(cuenta_pen) == Decimal("1000.00")

    def test_exige_identidad_verificada(self, api, cliente, cuenta_pen, cuenta_pen_2):
        cliente.is_identity_verified = False
        cliente.save()
        assert _propia(api, cuenta_pen, cuenta_pen_2).status_code == 403
        assert _saldo(cuenta_pen) == Decimal("1000.00")

    def test_entre_monedas_aplica_el_tipo_de_cambio(self, api, cuenta_pen, cuenta_usd, tipo_cambio):
        resp = _propia(api, cuenta_pen, cuenta_usd, monto="350.00")
        assert resp.status_code == 201
        assert resp.json()["kind"] == "currency_exchange"
        assert _saldo(cuenta_usd) == Decimal("200.00")


@pytest.mark.django_db
class TestTransferenciaATerceros:
    def test_interbancaria_por_cci(self, api, cliente, cuenta_pen):
        resp = _tercero(api, cuenta_pen)
        assert resp.status_code == 201, resp.content
        assert _saldo(cuenta_pen) == Decimal("900.00")

        tx = Transaction.objects.get()
        assert tx.kind == Transaction.Kind.INTERBANK_TRANSFER
        assert tx.destination_account is None
        assert tx.external_destination_number == CCI_EXTERNO
        assert tx.external_destination_holder == "Carla Ríos"
        assert tx.external_destination_bank == "Otro Banco"
        assert AuditLog.objects.filter(user=cliente, action="transfer.third_party").exists()

    def test_cobra_la_comision_interbancaria(self, api, cuenta_pen, settings):
        settings.INTERBANK_FEE = Decimal("2.50")
        assert _tercero(api, cuenta_pen).status_code == 201
        assert _saldo(cuenta_pen) == Decimal("897.50")
        assert Transaction.objects.get().fee == Decimal("2.50")

    def test_la_comision_cuenta_para_el_saldo(self, api, cuenta_pen, settings):
        settings.INTERBANK_FEE = Decimal("2.50")
        settings.TRANSFER_TOTP_THRESHOLD = {"PEN": Decimal("5000"), "USD": Decimal("5000")}
        resp = _tercero(api, cuenta_pen, monto="999.00")
        assert resp.status_code == 409
        assert _saldo(cuenta_pen) == Decimal("1000.00")

    def test_a_otro_cliente_de_luma(self, api, cuenta_pen, cuenta_ajena):
        resp = _tercero(api, cuenta_pen, cci=cuenta_ajena.number, holder="", bank="")
        assert resp.status_code == 201, resp.content
        assert _saldo(cuenta_ajena) == Decimal("100.00")
        assert Transaction.objects.get().kind == Transaction.Kind.THIRD_PARTY_TRANSFER

    @pytest.mark.parametrize(
        "cci", ["123", "0021930012345678901", "002193001234567890123", "0021930012345678901X"]
    )
    def test_valida_el_formato_del_cci(self, api, cuenta_pen, cci):
        resp = _tercero(api, cuenta_pen, cci=cci)
        assert resp.status_code == 400
        assert "20 dígitos" in str(resp.json())
        assert _saldo(cuenta_pen) == Decimal("1000.00")

    def test_rechaza_cci_inexistente_de_luma(self, api, cuenta_pen):
        resp = _tercero(api, cuenta_pen, cci="01100210000000000000")
        assert resp.status_code == 404

    def test_rechaza_cuenta_propia(self, api, cuenta_pen, cuenta_pen_2):
        resp = _tercero(api, cuenta_pen, cci=cuenta_pen_2.number)
        assert resp.status_code == 400
        assert resp.json()["code"] == "own_account"

    def test_pide_titular_y_banco_si_es_externa(self, api, cuenta_pen):
        resp = _tercero(api, cuenta_pen, holder="", bank="")
        assert resp.status_code == 400
        assert resp.json()["code"] == "external_data_required"

    def test_rechaza_otra_moneda_dentro_de_luma(self, api, cuenta_usd, cuenta_ajena):
        resp = _tercero(api, cuenta_usd, cci=cuenta_ajena.number, monto="10.00")
        assert resp.status_code == 400
        assert resp.json()["code"] == "currency_mismatch"

    def test_no_puede_usar_una_cuenta_ajena_como_origen(self, api, cuenta_ajena):
        assert _tercero(api, cuenta_ajena).status_code == 404


@pytest.mark.django_db
class TestUmbralTotp:
    def test_en_el_umbral_no_lo_pide(self, api, cuenta_pen, settings):
        settings.TRANSFER_TOTP_THRESHOLD = {"PEN": Decimal("100"), "USD": Decimal("100")}
        assert _tercero(api, cuenta_pen, monto="100.00").status_code == 201

    def test_sobre_el_umbral_lo_pide(self, api, cuenta_pen, settings):
        settings.TRANSFER_TOTP_THRESHOLD = {"PEN": Decimal("100"), "USD": Decimal("100")}
        resp = _tercero(api, cuenta_pen, monto="100.01")
        assert resp.status_code == 403
        assert resp.json()["code"] == "totp_required"
        assert _saldo(cuenta_pen) == Decimal("1000.00")

    def test_con_codigo_correcto_transfiere(self, api, cuenta_pen, settings, codigo_totp):
        settings.TRANSFER_TOTP_THRESHOLD = {"PEN": Decimal("100"), "USD": Decimal("100")}
        assert _tercero(api, cuenta_pen, monto="200.00", totp=codigo_totp).status_code == 201
        assert _saldo(cuenta_pen) == Decimal("800.00")

    def test_con_codigo_incorrecto_no_transfiere(self, api, cuenta_pen, settings):
        settings.TRANSFER_TOTP_THRESHOLD = {"PEN": Decimal("100"), "USD": Decimal("100")}
        resp = _tercero(api, cuenta_pen, monto="200.00", totp="000000")
        assert resp.status_code == 403
        assert resp.json()["code"] == "totp_invalid"
        assert _saldo(cuenta_pen) == Decimal("1000.00")

    def test_cinco_codigos_incorrectos_bloquean(self, api, cliente, cuenta_pen, settings):
        settings.TRANSFER_TOTP_THRESHOLD = {"PEN": Decimal("100"), "USD": Decimal("100")}
        for _ in range(4):
            _tercero(api, cuenta_pen, monto="200.00", totp="000000")
        quinto = _tercero(api, cuenta_pen, monto="200.00", totp="000000")
        assert quinto.status_code == 423
        cliente.refresh_from_db()
        assert cliente.locked_until is not None
        assert _saldo(cuenta_pen) == Decimal("1000.00")


@pytest.mark.django_db
class TestConversion:
    def _convertir(self, api, origen, destino, monto):
        return api.post(
            reverse("banking:exchange"),
            {"source_number": origen.number, "destination_number": destino.number, "amount": monto},
            format="json",
        )

    def test_soles_a_dolares_a_precio_de_venta(self, api, cuenta_pen, cuenta_usd, tipo_cambio):
        resp = self._convertir(api, cuenta_pen, cuenta_usd, "350.00")
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body["exchange_rate"] == "3.5000"
        assert body["destination_amount"] == "100.00"
        assert body["destination_currency"] == "USD"
        assert _saldo(cuenta_pen) == Decimal("650.00")
        assert _saldo(cuenta_usd) == Decimal("200.00")

    def test_dolares_a_soles_a_precio_de_compra(self, api, cuenta_pen, cuenta_usd, tipo_cambio):
        resp = self._convertir(api, cuenta_usd, cuenta_pen, "10.00")
        assert resp.status_code == 201
        assert resp.json()["exchange_rate"] == "3.4000"
        assert _saldo(cuenta_usd) == Decimal("90.00")
        assert _saldo(cuenta_pen) == Decimal("1034.00")

    def test_historial_muestra_cada_lado_en_su_moneda(
        self, api, cuenta_pen, cuenta_usd, tipo_cambio
    ):
        self._convertir(api, cuenta_pen, cuenta_usd, "350.00")
        cargo = api.get(reverse("banking:account-transactions", args=[cuenta_pen.number])).json()[
            "results"
        ][0]
        abono = api.get(reverse("banking:account-transactions", args=[cuenta_usd.number])).json()[
            "results"
        ][0]
        assert (cargo["amount"], cargo["currency"]) == ("350.00", "PEN")
        assert (abono["amount"], abono["currency"]) == ("100.00", "USD")
        assert abono["exchange_rate"] == "3.5000"

    def test_rechaza_la_misma_moneda(self, api, cuenta_pen, cuenta_pen_2, tipo_cambio):
        resp = self._convertir(api, cuenta_pen, cuenta_pen_2, "10.00")
        assert resp.status_code == 400
        assert resp.json()["code"] == "same_currency"

    def test_saldo_insuficiente(self, api, cuenta_pen, cuenta_usd, tipo_cambio):
        assert self._convertir(api, cuenta_pen, cuenta_usd, "5000.00").status_code == 409
        assert _saldo(cuenta_usd) == Decimal("100.00")

    def test_monto_que_redondea_a_cero(self, api, cuenta_pen, cuenta_usd, tipo_cambio):
        resp = self._convertir(api, cuenta_pen, cuenta_usd, "0.01")
        assert resp.status_code == 400
        assert resp.json()["code"] == "amount_too_low"

    def test_sin_tipo_de_cambio_no_convierte(self, api, cuenta_pen, cuenta_usd):
        resp = self._convertir(api, cuenta_pen, cuenta_usd, "10.00")
        assert resp.status_code == 503
        assert resp.json()["code"] == "exchange_rate_unavailable"
        assert _saldo(cuenta_pen) == Decimal("1000.00")

    def test_cotizacion(self, api, tipo_cambio):
        resp = api.get(
            reverse("banking:exchange-quote"),
            {"amount": "35.00", "from_currency": "PEN", "to_currency": "USD"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["credited"] == "10.00"
        assert body["applied_rate"] == "3.5000"
        assert body["date"] == timezone.localdate().isoformat()
        assert body["source"] == "SUNAT"


@pytest.mark.django_db
class TestComprobante:
    def test_descarga_un_pdf(self, api, cuenta_pen):
        codigo = _tercero(api, cuenta_pen).json()["operation_code"]
        resp = api.get(reverse("banking:receipt", args=[codigo]))
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"
        assert codigo in resp["Content-Disposition"]
        assert resp.content.startswith(b"%PDF")

    def test_contiene_los_datos_de_la_operacion(self, api, cuenta_pen):
        codigo = _tercero(api, cuenta_pen, concept="Alquiler").json()["operation_code"]
        filas = dict(_rows(Transaction.objects.get(operation_code=codigo)))
        assert filas["Código de operación"] == codigo
        assert filas["Titular de destino"] == "Carla Ríos"
        assert filas["Concepto"] == "Alquiler"
        assert filas["Monto"] == "PEN 100.00"
        # El número completo de la cuenta destino no aparece en el comprobante.
        assert filas["Cuenta de destino"] == f"****{CCI_EXTERNO[-4:]}"

    def test_no_se_puede_ver_el_de_otro_cliente(self, api, cuenta_ajena, otro_cliente):
        cuenta_ajena.balance = Decimal("50.00")
        cuenta_ajena.save()
        ajeno = APIClient()
        ajeno.force_authenticate(otro_cliente)
        codigo = _tercero(ajeno, cuenta_ajena, monto="10.00").json()["operation_code"]
        assert api.get(reverse("banking:receipt", args=[codigo])).status_code == 404

    def test_el_destinatario_no_descarga_el_comprobante(
        self, api, cuenta_pen, cuenta_ajena, otro_cliente
    ):
        codigo = _tercero(api, cuenta_pen, cci=cuenta_ajena.number).json()["operation_code"]
        destinatario = APIClient()
        destinatario.force_authenticate(otro_cliente)
        assert destinatario.get(reverse("banking:receipt", args=[codigo])).status_code == 404
