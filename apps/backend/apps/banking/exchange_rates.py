"""
Tipo de cambio oficial publicado por SUNAT.

SUNAT publica un TXT con una línea `dd/mm/aaaa|compra|venta|`. Cada día se guarda
en `tipo_cambio`; si la consulta falla se sigue usando la última publicación
guardada, salvo que sea demasiado antigua para considerarla vigente.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import ExchangeRate

logger = logging.getLogger("luma.banking")

_FETCH_LOCK_KEY = "exchange_rate:fetch"
_FETCH_LOCK_SECONDS = 60 * 60
_TIMEOUT_SECONDS = 5


class ExchangeRateUnavailable(Exception):
    pass


def _parse(text: str) -> tuple:
    fecha, compra, venta = text.strip().split("|")[:3]
    date = datetime.strptime(fecha, "%d/%m/%Y").date()
    buy, sell = Decimal(compra), Decimal(venta)
    if buy <= 0 or sell < buy:
        raise ValueError(f"Valores incoherentes: compra={buy} venta={sell}")
    return date, buy, sell


def refresh_rate() -> None:
    """Consulta a SUNAT y guarda lo publicado. Un fallo solo se registra."""
    try:
        response = requests.get(settings.EXCHANGE_RATE_URL, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
        date, buy, sell = _parse(response.text)
    except (requests.RequestException, ValueError, InvalidOperation) as exc:
        logger.warning("No se pudo actualizar el tipo de cambio: %s", exc)
        return
    ExchangeRate.objects.update_or_create(
        date=date, defaults={"buy": buy, "sell": sell, "source": "SUNAT"}
    )


def current_rate() -> ExchangeRate:
    today = timezone.localdate()
    rate = ExchangeRate.objects.order_by("-date").first()
    # SUNAT no publica todos los días: como máximo se le consulta una vez por hora.
    if (rate is None or rate.date < today) and cache.add(_FETCH_LOCK_KEY, 1, _FETCH_LOCK_SECONDS):
        refresh_rate()
        rate = ExchangeRate.objects.order_by("-date").first()

    oldest_valid = today - timedelta(days=settings.EXCHANGE_RATE_MAX_AGE_DAYS)
    if rate is None or rate.date < oldest_valid:
        raise ExchangeRateUnavailable("No hay un tipo de cambio vigente.")
    return rate
