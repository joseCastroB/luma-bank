"""Devengo diario, capitalización mensual y consulta del tipo de cambio."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock

import pytest
import requests
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.banking import exchange_rates
from apps.banking.interest import accrue_account, accrue_all, daily_rate
from apps.banking.models import Account, ExchangeRate, SavingsRate, Transaction


def _fijar_ultimo_devengo(cuenta, dia):
    Account.objects.filter(pk=cuenta.pk).update(last_accrual_on=dia)


@pytest.mark.django_db
class TestDevengo:
    def test_tasa_diaria_compone_a_la_trea(self):
        assert (1 + daily_rate(Decimal("4.00"))) ** 365 == pytest.approx(Decimal("1.04"))

    def test_un_dia_devenga_sin_tocar_el_saldo(self, cuenta_pen, tasas):
        _fijar_ultimo_devengo(cuenta_pen, date(2026, 3, 10))
        assert accrue_account(cuenta_pen.pk, until=date(2026, 3, 11)) == 1

        cuenta = Account.objects.get(pk=cuenta_pen.pk)
        assert cuenta.balance == Decimal("1000.00")
        assert cuenta.accrued_interest == pytest.approx(Decimal("0.107"), abs=Decimal("0.001"))
        assert cuenta.last_accrual_on == date(2026, 3, 11)

    def test_correrlo_dos_veces_no_duplica(self, cuenta_pen, tasas):
        _fijar_ultimo_devengo(cuenta_pen, date(2026, 3, 10))
        accrue_account(cuenta_pen.pk, until=date(2026, 3, 11))
        primero = Account.objects.get(pk=cuenta_pen.pk).accrued_interest
        assert accrue_account(cuenta_pen.pk, until=date(2026, 3, 11)) == 0
        assert Account.objects.get(pk=cuenta_pen.pk).accrued_interest == primero

    def test_se_pone_al_dia_si_falto_correrlo(self, cuenta_pen, tasas):
        _fijar_ultimo_devengo(cuenta_pen, date(2026, 3, 10))
        assert accrue_account(cuenta_pen.pk, until=date(2026, 3, 15)) == 5

    def test_usa_la_trea_vigente_de_cada_dia(self, cuenta_pen, tasas):
        SavingsRate.objects.create(
            currency="PEN", trea=Decimal("8.00"), valid_from=date(2026, 3, 11)
        )
        _fijar_ultimo_devengo(cuenta_pen, date(2026, 3, 9))
        accrue_account(cuenta_pen.pk, until=date(2026, 3, 11))
        esperado = Decimal("1000") * daily_rate(Decimal("4.00")) + Decimal("1000") * daily_rate(
            Decimal("8.00")
        )
        cuenta = Account.objects.get(pk=cuenta_pen.pk)
        assert cuenta.accrued_interest == pytest.approx(esperado, abs=Decimal("0.00001"))

    def test_cuenta_sin_saldo_no_gana_interes(self, cuenta_pen_2, tasas):
        _fijar_ultimo_devengo(cuenta_pen_2, date(2026, 3, 10))
        accrue_account(cuenta_pen_2.pk, until=date(2026, 3, 11))
        assert Account.objects.get(pk=cuenta_pen_2.pk).accrued_interest == 0

    def test_cuenta_congelada_no_se_procesa(self, cuenta_pen, tasas):
        Account.objects.filter(pk=cuenta_pen.pk).update(status=Account.Status.FROZEN)
        assert accrue_account(cuenta_pen.pk, until=date(2026, 3, 11)) == 0


@pytest.mark.django_db
class TestCapitalizacion:
    def test_a_fin_de_mes_suma_el_interes_al_saldo(self, cuenta_pen, tasas):
        _fijar_ultimo_devengo(cuenta_pen, date(2026, 2, 28))
        accrue_account(cuenta_pen.pk, until=date(2026, 3, 31))

        cuenta = Account.objects.get(pk=cuenta_pen.pk)
        tx = Transaction.objects.get(kind=Transaction.Kind.INTEREST)
        assert tx.destination_account_id == cuenta.pk
        assert tx.source_account is None
        assert tx.status == Transaction.Status.COMPLETED
        assert cuenta.balance == Decimal("1000.00") + tx.amount
        assert tx.destination_balance_after == cuenta.balance
        # Marzo tiene 31 días: unos S/ 3.33 a 4% TREA.
        assert tx.amount == pytest.approx(Decimal("3.33"), abs=Decimal("0.03"))
        # Las fracciones de centavo quedan devengadas para el mes siguiente.
        assert Decimal("0") <= cuenta.accrued_interest < Decimal("0.01")

    def test_antes_del_cierre_no_capitaliza(self, cuenta_pen, tasas):
        _fijar_ultimo_devengo(cuenta_pen, date(2026, 2, 28))
        accrue_account(cuenta_pen.pk, until=date(2026, 3, 30))
        assert not Transaction.objects.exists()

    def test_el_interes_gana_interes_el_mes_siguiente(self, cuenta_pen, tasas):
        _fijar_ultimo_devengo(cuenta_pen, date(2026, 2, 28))
        accrue_account(cuenta_pen.pk, until=date(2026, 4, 30))
        assert Transaction.objects.filter(kind=Transaction.Kind.INTEREST).count() == 2
        assert Account.objects.get(pk=cuenta_pen.pk).balance > Decimal("1006")

    def test_comando_procesa_todas_las_cuentas(self, cuenta_pen, cuenta_usd, tasas):
        ayer = timezone.localdate() - timedelta(days=1)
        _fijar_ultimo_devengo(cuenta_pen, ayer - timedelta(days=1))
        _fijar_ultimo_devengo(cuenta_usd, ayer - timedelta(days=1))
        call_command("devengar_intereses")
        for cuenta in (cuenta_pen, cuenta_usd):
            assert Account.objects.get(pk=cuenta.pk).last_accrual_on == ayer
        assert accrue_all() == 0


@pytest.mark.django_db
class TestDeposito:
    def test_abona_y_registra(self, cuenta_pen_2, settings):
        settings.DEBUG = True
        call_command("depositar", cuenta_pen_2.number, "250.50")
        assert Account.objects.get(pk=cuenta_pen_2.pk).balance == Decimal("250.50")
        assert Transaction.objects.get().kind == Transaction.Kind.DEPOSIT

    def test_no_funciona_fuera_de_desarrollo(self, cuenta_pen_2, settings):
        settings.DEBUG = False
        with pytest.raises(CommandError):
            call_command("depositar", cuenta_pen_2.number, "250.50")
        assert Account.objects.get(pk=cuenta_pen_2.pk).balance == 0


def _respuesta(texto):
    return Mock(text=texto, raise_for_status=Mock())


@pytest.mark.django_db
class TestTipoDeCambio:
    def test_guarda_lo_publicado_por_sunat(self, monkeypatch):
        hoy = timezone.localdate()
        monkeypatch.setattr(
            requests, "get", lambda *a, **k: _respuesta(f"{hoy:%d/%m/%Y}|3.458|3.467|\n")
        )
        rate = exchange_rates.current_rate()
        assert (rate.date, rate.buy, rate.sell) == (hoy, Decimal("3.458"), Decimal("3.467"))
        assert rate.source == "SUNAT"

    def test_no_consulta_si_ya_tiene_el_de_hoy(self, tipo_cambio, monkeypatch):
        llamada = Mock()
        monkeypatch.setattr(requests, "get", llamada)
        assert exchange_rates.current_rate() == tipo_cambio
        llamada.assert_not_called()

    def test_consulta_como_maximo_una_vez_por_hora(self, monkeypatch):
        llamada = Mock(side_effect=requests.ConnectionError())
        monkeypatch.setattr(requests, "get", llamada)
        for _ in range(3):
            with pytest.raises(exchange_rates.ExchangeRateUnavailable):
                exchange_rates.current_rate()
        assert llamada.call_count == 1

    def test_si_falla_usa_la_ultima_publicacion(self):
        ayer = timezone.localdate() - timedelta(days=1)
        anterior = ExchangeRate.objects.create(date=ayer, buy=Decimal("3.4"), sell=Decimal("3.5"))
        assert exchange_rates.current_rate() == anterior

    def test_no_usa_una_publicacion_demasiado_antigua(self, settings):
        viejo = timezone.localdate() - timedelta(days=settings.EXCHANGE_RATE_MAX_AGE_DAYS + 1)
        ExchangeRate.objects.create(date=viejo, buy=Decimal("3.4"), sell=Decimal("3.5"))
        with pytest.raises(exchange_rates.ExchangeRateUnavailable):
            exchange_rates.current_rate()

    @pytest.mark.parametrize(
        "texto", ["<html>error</html>", "", "02/11/2026|abc|3.4|", "02/11/2026|3.5|3.4|"]
    )
    def test_ignora_una_respuesta_invalida(self, monkeypatch, texto):
        monkeypatch.setattr(requests, "get", lambda *a, **k: _respuesta(texto))
        with pytest.raises(exchange_rates.ExchangeRateUnavailable):
            exchange_rates.current_rate()
        assert not ExchangeRate.objects.exists()
