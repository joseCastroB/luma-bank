"""
Modelos del dominio de cuentas / clientes.

Se define un User personalizado DESDE EL SPRINT 0 (aunque casi vacio) porque
cambiar AUTH_USER_MODEL despues de la primera migracion es muy costoso.

Los campos de KYC facial (HU02) se agregaran aqui en el Sprint 1:
- referencia al objeto del embedding cifrado en MinIO (NUNCA el embedding)
- estado de verificacion RENIEC
- contador de intentos de login y bloqueo temporal (HU03)
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Usuario base. Se extendera en el Sprint 1 (registro/login facial)."""

    # El DNI (8 digitos) sera el identificador de negocio del cliente.
    dni = models.CharField(
        "DNI",
        max_length=8,
        unique=True,
        null=True,
        blank=True,
        help_text="Documento Nacional de Identidad (8 digitos).",
    )

    class Meta:
        db_table = "accounts_user"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self) -> str:
        return self.get_username()
