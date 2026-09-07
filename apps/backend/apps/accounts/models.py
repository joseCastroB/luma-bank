"""
Modelos del dominio de cuentas / clientes.

User personalizado desde el Sprint 0. En el Sprint 1 (HU02/HU03) se agregan:
- email obligatorio y único (identificador del login alterno)
- fecha de nacimiento autodeclarada (+18)
- verificación de identidad vía RENIEC
- secreto TOTP cifrado en reposo (segundo factor del método alterno)
- FaceEmbedding: referencia al objeto cifrado en MinIO (NUNCA el embedding aquí)
- DniValidationLog: auditoría de consultas de identidad
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Cliente de Luma Bank."""

    # email pasa a ser obligatorio y único (AbstractUser lo trae opcional).
    email = models.EmailField("correo electrónico", unique=True)

    dni = models.CharField(
        "DNI",
        max_length=8,
        unique=True,
        null=True,
        blank=True,
        help_text="Documento Nacional de Identidad (8 dígitos).",
    )
    birth_date = models.DateField("fecha de nacimiento", null=True, blank=True)

    is_identity_verified = models.BooleanField(
        "identidad verificada (RENIEC)",
        default=False,
    )

    # Secreto TOTP cifrado (AES-256-GCM + base64). Ver services/crypto.py.
    totp_secret_encrypted = models.CharField(max_length=255, blank=True, default="")

    USERNAME_FIELD = "username"  # se mantiene; username = email en el registro
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "accounts_user"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self) -> str:
        return self.email or self.get_username()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def has_totp(self) -> bool:
        return bool(self.totp_secret_encrypted)


class FaceEmbedding(models.Model):
    """
    Referencia al embedding facial del usuario.

    El vector se cifra (AES-256-GCM) y se guarda como objeto en MinIO. Aquí solo
    quedan la ubicación y metadatos: nunca el vector ni una foto.
    """

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="face_embedding",
    )
    bucket = models.CharField(max_length=128)
    object_key = models.CharField(max_length=256)
    algorithm = models.CharField(
        max_length=128,
        help_text="Modelo/versión que generó el vector, p. ej. 'face-api ssdMobilenetv1 128d'.",
    )
    dimensions = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_face_embedding"
        verbose_name = "embedding facial"
        verbose_name_plural = "embeddings faciales"

    def __str__(self) -> str:
        return f"FaceEmbedding<{self.user_id}> {self.object_key}"


class DniValidationLog(models.Model):
    """Auditoría de cada consulta de identidad (RENIEC vía LionAPI o mock)."""

    class Mode(models.TextChoices):
        PRODUCTION = "production", "production"
        MOCK = "mock", "mock"

    class Result(models.TextChoices):
        FOUND = "found", "encontrado"
        NOT_FOUND = "not_found", "no encontrado"
        INVALID = "invalid", "DNI inválido"
        ERROR = "error", "error del servicio"
        CACHED = "cached", "desde caché"

    dni = models.CharField(max_length=16)
    mode = models.CharField(max_length=16, choices=Mode.choices)
    result = models.CharField(max_length=16, choices=Result.choices)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "accounts_dni_validation_log"
        indexes = [models.Index(fields=["dni", "created_at"])]

    def __str__(self) -> str:
        return f"{self.dni} [{self.mode}] -> {self.result}"
