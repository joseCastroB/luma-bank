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
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Cliente de Luma Bank."""

    # Campos heredados de AbstractUser, redefinidos solo para que la columna
    # tenga nombre en español. El comportamiento es el mismo de Django.
    password = models.CharField("contraseña", max_length=128, db_column="clave")
    last_login = models.DateTimeField(
        "último acceso", blank=True, null=True, db_column="ultimo_acceso"
    )
    is_superuser = models.BooleanField(
        "es superusuario", default=False, db_column="es_superusuario"
    )
    username = models.CharField(
        "nombre de usuario",
        max_length=150,
        unique=True,
        validators=[UnicodeUsernameValidator()],
        error_messages={"unique": "Ya existe un usuario con ese nombre."},
        db_column="nombre_usuario",
    )
    first_name = models.CharField("nombres", max_length=150, blank=True, db_column="nombres")
    last_name = models.CharField("apellidos", max_length=150, blank=True, db_column="apellidos")
    is_staff = models.BooleanField("es personal", default=False, db_column="es_personal")
    is_active = models.BooleanField("activo", default=True, db_column="esta_activo")
    date_joined = models.DateTimeField(
        "fecha de registro", default=timezone.now, db_column="fecha_registro"
    )

    # email pasa a ser obligatorio y único (AbstractUser lo trae opcional).
    email = models.EmailField("correo electrónico", unique=True, db_column="correo")

    dni = models.CharField(
        "DNI",
        max_length=8,
        unique=True,
        null=True,
        blank=True,
        help_text="Documento Nacional de Identidad (8 dígitos).",
        db_column="dni",
    )
    birth_date = models.DateField(
        "fecha de nacimiento", null=True, blank=True, db_column="fecha_nacimiento"
    )

    is_identity_verified = models.BooleanField(
        "identidad verificada (RENIEC)", default=False, db_column="identidad_verificada"
    )

    # Secreto TOTP cifrado (AES-256-GCM + base64). Ver services/crypto.py.
    totp_secret_encrypted = models.CharField(
        max_length=255, blank=True, default="", db_column="secreto_totp_cifrado"
    )

    # --- Política de intentos de login (HU03) ---
    failed_facial_attempts = models.PositiveSmallIntegerField(
        default=0, db_column="intentos_faciales_fallidos"
    )
    failed_login_attempts = models.PositiveSmallIntegerField(
        default=0, db_column="intentos_login_fallidos"
    )
    locked_until = models.DateTimeField(null=True, blank=True, db_column="bloqueado_hasta")

    USERNAME_FIELD = "username"  # se mantiene; username = email en el registro
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "usuario"
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
        db_column="usuario_id",
    )
    bucket = models.CharField(max_length=128, db_column="bucket")
    object_key = models.CharField(max_length=256, db_column="clave_objeto")
    algorithm = models.CharField(
        max_length=128,
        help_text="Modelo/versión que generó el vector, p. ej. 'face-api ssdMobilenetv1 128d'.",
        db_column="algoritmo",
    )
    dimensions = models.PositiveIntegerField(db_column="dimensiones")
    created_at = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")
    updated_at = models.DateTimeField(auto_now=True, db_column="fecha_actualizacion")

    class Meta:
        db_table = "embedding_facial"
        verbose_name = "embedding facial"
        verbose_name_plural = "embeddings faciales"

    def __str__(self) -> str:
        return f"FaceEmbedding<{self.user_id}> {self.object_key}"


class LoginAttempt(models.Model):
    """Auditoría de cada intento de inicio de sesión (HU03)."""

    class Method(models.TextChoices):
        FACIAL = "facial", "reconocimiento facial"
        PASSWORD_TOTP = "password_totp", "contraseña + TOTP"

    class Outcome(models.TextChoices):
        SUCCESS = "success", "éxito"
        BAD_FACE = "bad_face", "rostro no coincide"
        BAD_LIVENESS = "bad_liveness", "prueba de vida fallida (sospechoso)"
        BAD_PASSWORD = "bad_password", "contraseña incorrecta"
        BAD_TOTP = "bad_totp", "código TOTP incorrecto"
        LOCKED = "locked", "cuenta bloqueada"
        UNKNOWN_USER = "unknown_user", "usuario no encontrado"

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="login_attempts",
        db_column="usuario_id",
    )
    identifier = models.CharField(
        max_length=254, help_text="email o DNI ingresado", db_column="identificador"
    )
    method = models.CharField(max_length=20, choices=Method.choices, db_column="metodo")
    outcome = models.CharField(max_length=20, choices=Outcome.choices, db_column="resultado")
    suspicious = models.BooleanField(default=False, db_column="sospechoso")
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_column="direccion_ip")
    user_agent = models.CharField(
        max_length=300, blank=True, default="", db_column="agente_usuario"
    )
    created_at = models.DateTimeField(default=timezone.now, db_column="fecha_creacion")

    class Meta:
        db_table = "intento_login"
        indexes = [models.Index(fields=["identifier", "created_at"])]

    def __str__(self) -> str:
        return f"{self.identifier} [{self.method}] -> {self.outcome}"


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

    dni = models.CharField(max_length=16, db_column="dni")
    mode = models.CharField(max_length=16, choices=Mode.choices, db_column="modo")
    result = models.CharField(max_length=16, choices=Result.choices, db_column="resultado")
    created_at = models.DateTimeField(default=timezone.now, db_column="fecha_creacion")

    class Meta:
        db_table = "registro_validacion_dni"
        indexes = [models.Index(fields=["dni", "created_at"])]

    def __str__(self) -> str:
        return f"{self.dni} [{self.mode}] -> {self.result}"


class Notification(models.Model):
    """Aviso mostrado al cliente dentro de la banca web."""

    class Kind(models.TextChoices):
        SECURITY = "security", "seguridad"
        TRANSFER = "transfer", "transferencia"
        CARD = "card", "tarjeta"
        LOAN = "loan", "préstamo"
        SYSTEM = "system", "sistema"

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notifications",
        db_column="usuario_id",
    )
    kind = models.CharField(max_length=16, choices=Kind.choices, db_column="tipo")
    title = models.CharField(max_length=120, db_column="titulo")
    body = models.CharField(max_length=500, blank=True, default="", db_column="mensaje")
    read_at = models.DateTimeField(null=True, blank=True, db_column="fecha_lectura")
    created_at = models.DateTimeField(default=timezone.now, db_column="fecha_creacion")

    class Meta:
        db_table = "notificacion"
        indexes = [models.Index(fields=["user", "created_at"])]

    def __str__(self) -> str:
        return f"{self.user_id} [{self.kind}] {self.title}"


class AuditLog(models.Model):
    """
    Bitácora de acciones sensibles (cambios de datos, bloqueos, operaciones).

    Es de solo inserción. `metadata` no debe contener datos sensibles en claro
    (contraseñas, tokens, números de tarjeta).
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        db_column="usuario_id",
    )
    action = models.CharField(
        max_length=64, help_text="p. ej. 'transfer.create', 'card.block'", db_column="accion"
    )
    entity = models.CharField(max_length=64, blank=True, default="", db_column="entidad")
    entity_id = models.CharField(max_length=64, blank=True, default="", db_column="entidad_id")
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_column="direccion_ip")
    metadata = models.JSONField(default=dict, blank=True, db_column="metadatos")
    created_at = models.DateTimeField(default=timezone.now, db_column="fecha_creacion")

    class Meta:
        db_table = "bitacora_auditoria"
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["entity", "entity_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.entity}:{self.entity_id}"
