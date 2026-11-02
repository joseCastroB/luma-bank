"""Registro de acciones sensibles en la bitácora de auditoría."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv46_address

from ..models import AuditLog


def client_ip(request) -> str | None:
    """IP del cliente, o None si no es válida (X-Forwarded-For lo controla quien llama)."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    try:
        validate_ipv46_address(ip)
    except ValidationError:
        return None
    return ip


def record(request, action: str, *, entity: str, entity_id: str, **metadata) -> AuditLog:
    """`metadata` no debe llevar datos sensibles en claro."""
    return AuditLog.objects.create(
        user=request.user,
        action=action,
        entity=entity,
        entity_id=entity_id,
        ip_address=client_ip(request),
        metadata=metadata,
    )
