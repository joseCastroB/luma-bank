"""Avisos de seguridad por correo. Un fallo de correo nunca interrumpe la operación."""

from __future__ import annotations

import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger("luma.auth")


def _send(user, subject: str, message: str) -> None:
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
    except (SMTPException, OSError):
        logger.exception("No se pudo enviar el aviso de seguridad al usuario %s", user.pk)


def notify_account_locked(user) -> None:
    until = timezone.localtime(user.locked_until)
    _send(
        user,
        "Bloqueamos tu acceso a Luma Bank",
        f"Hola, {user.first_name or user.email}.\n\n"
        "Detectamos varios intentos fallidos de acceso a tu cuenta y la bloqueamos "
        f"temporalmente por seguridad. Podrás volver a intentarlo a partir del "
        f"{until:%d/%m/%Y a las %H:%M}.\n\n"
        "Si no fuiste tú, contacta a soporte de Luma Bank.",
    )


def notify_biometrics_updated(user) -> None:
    _send(
        user,
        "Actualizaste tu rostro en Luma Bank",
        f"Hola, {user.first_name or user.email}.\n\n"
        "Se actualizaron los datos biométricos de tu cuenta.\n\n"
        "Si no fuiste tú, contacta a soporte de Luma Bank de inmediato.",
    )
