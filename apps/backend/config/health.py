"""Endpoint de health check. Publico, sin autenticacion."""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(_request: Request) -> Response:
    """Reporta el estado del servicio y sus dependencias."""
    checks: dict[str, str] = {}

    try:
        connection.ensure_connection()
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"

    try:
        cache.set("healthcheck", "1", 5)
        checks["cache"] = "ok" if cache.get("healthcheck") == "1" else "error"
    except Exception as exc:  # noqa: BLE001
        checks["cache"] = f"error: {exc}"

    healthy = all(v == "ok" for v in checks.values())
    return Response(
        {
            "status": "ok" if healthy else "degraded",
            "service": "luma-bank-api",
            "dni_validation_mode": settings.DNI_VALIDATION_MODE,
            "debug": settings.DEBUG,
            "checks": checks,
        },
        status=200 if healthy else 503,
    )
