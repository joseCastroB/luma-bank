"""
Lógica de inicio de sesión (HU03).

- Reconocimiento facial: compara el descriptor en vivo contra el EMBEDDING
  almacenado (se descifra en memoria; nunca se guarda en claro).
- Método alterno: contraseña + TOTP.
- Política de bloqueo:
    * >= LOGIN_MAX_FACIAL_ATTEMPTS fallos faciales -> se ofrece el método alterno.
    * >= LOGIN_MAX_TOTAL_ATTEMPTS fallos (faciales o TOTP) -> cuenta bloqueada
      ACCOUNT_LOCK_MINUTES minutos.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

import pyotp
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from . import crypto, face_store

logger = logging.getLogger("luma.auth")
User = get_user_model()


class LoginError(Exception):
    def __init__(
        self, message: str, *, code: str = "", status: int = 401, extra: dict | None = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.extra = extra or {}


@dataclass
class FaceCheck:
    matched: bool
    distance: float


def resolve_user(identifier: str):
    ident = (identifier or "").strip()
    if not ident:
        return None
    if "@" in ident:
        return User.objects.filter(email__iexact=ident).first()
    if ident.isdigit():
        return User.objects.filter(dni=ident).first()
    return User.objects.filter(email__iexact=ident).first()


# --- Bloqueo -----------------------------------------------------------


def is_locked(user) -> bool:
    return bool(user.locked_until and user.locked_until > timezone.now())


def _register_failure(user, *, facial: bool) -> bool:
    """Suma el fallo. Devuelve True si con esto la cuenta quedó bloqueada."""
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if facial:
        user.failed_facial_attempts = (user.failed_facial_attempts or 0) + 1

    locked = False
    if user.failed_login_attempts >= settings.LOGIN_MAX_TOTAL_ATTEMPTS:
        user.locked_until = timezone.now() + timedelta(minutes=settings.ACCOUNT_LOCK_MINUTES)
        locked = True
    user.save(update_fields=["failed_login_attempts", "failed_facial_attempts", "locked_until"])
    return locked


def reset_failures(user) -> None:
    User.objects.filter(pk=user.pk).update(
        failed_login_attempts=0, failed_facial_attempts=0, locked_until=None
    )
    user.failed_login_attempts = 0
    user.failed_facial_attempts = 0
    user.locked_until = None


def should_offer_fallback(user) -> bool:
    return (user.failed_facial_attempts or 0) >= settings.LOGIN_MAX_FACIAL_ATTEMPTS


# --- Verificación facial --------------------------------------------


def verify_face(user, descriptor: list[float]) -> FaceCheck:
    ref = getattr(user, "face_embedding", None)
    if ref is None:
        raise LoginError("El usuario no tiene un rostro registrado.", code="no_face", status=400)

    blob = face_store.get_embedding(ref.bucket, ref.object_key)
    stored = crypto.decrypt_embedding(blob)

    distance = _euclidean(stored, descriptor)
    return FaceCheck(matched=distance <= settings.FACE_MATCH_THRESHOLD, distance=distance)


def _euclidean(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    return sum((a[i] - b[i]) ** 2 for i in range(n)) ** 0.5


# --- Verificación TOTP ---------------------------------------------


def verify_totp(user, code: str) -> bool:
    if not user.totp_secret_encrypted:
        return False
    secret = crypto.decrypt_secret(user.totp_secret_encrypted)
    return pyotp.TOTP(secret).verify((code or "").strip(), valid_window=1)
