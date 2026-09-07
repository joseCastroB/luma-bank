"""
Configuracion base de Luma Bank. Compartida por dev.py y prod.py.

Nunca se usa directamente: DJANGO_SETTINGS_MODULE debe apuntar a
`config.settings.dev` o `config.settings.prod`.
"""

from __future__ import annotations

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

# apps/backend/  (donde vive manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

# Lee un archivo .env si esta presente (util al correr fuera de Docker).
# En Docker las variables llegan por el entorno del contenedor (env_file).
_dotenv = BASE_DIR / ".env"
if _dotenv.exists():
    env.read_env(str(_dotenv))

# ---------------------------------------------------------------------------
# Nucleo
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    "corsheaders",
    # Apps de dominio
    "apps.accounts",
    "apps.banking",
    "apps.cards",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Base de datos (PostgreSQL 18) - se toma de DATABASE_URL
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://luma:luma@localhost:5432/luma",
    ),
}
DATABASES["default"].setdefault("CONN_MAX_AGE", 60)

# ---------------------------------------------------------------------------
# Cache y sesiones (Valkey 8) - se toma de REDIS_URL
# ---------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    },
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ---------------------------------------------------------------------------
# Autenticacion / passwords (OWASP ASVS L2)
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internacionalizacion
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "es-pe"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos estaticos y media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/min",
        "user": "120/min",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[FRONTEND_URL])
CORS_ALLOW_CREDENTIALS = True

# ===========================================================================
# Configuracion de dominio - Luma Bank
# ===========================================================================

# --- Validacion de identidad (RENIEC via LionAPI) --------------------------
# CRITICO (fail-safe): si DNI_VALIDATION_MODE no esta definido, se comporta
# como "production", NUNCA como "mock". El modo "mock" solo debe usarse en
# desarrollo y en tests automatizados.
DNI_VALIDATION_MODE = env("DNI_VALIDATION_MODE", default="production")
if DNI_VALIDATION_MODE not in {"production", "mock"}:
    raise ImproperlyConfigured(
        f"DNI_VALIDATION_MODE invalido: {DNI_VALIDATION_MODE!r}. "
        "Valores permitidos: 'production' | 'mock'."
    )

LIONAPI_KEY = env("LIONAPI_KEY", default="")
LIONAPI_BASE_URL = env(
    "LIONAPI_BASE_URL",
    default="https://www.softwarelion.pe/api/lion-api/v1",
)
# TTL del cache por DNI (creditos limitados: plan gratuito 90/mes).
LIONAPI_CACHE_TTL_SECONDS = env.int("LIONAPI_CACHE_TTL_SECONDS", default=60 * 60 * 24 * 30)

# --- Reconocimiento facial ------------------------------------------------
# El login compara el rostro en vivo contra el EMBEDDING almacenado.
# Umbral de distancia: menor = mas estricto. Depende del modelo usado.
FACE_MATCH_THRESHOLD = env.float("FACE_MATCH_THRESHOLD", default=0.6)

# --- Almacenamiento de embeddings faciales (MinIO / S3) ------------------
# El embedding se cifra (AES-256) y se guarda en MinIO. En PostgreSQL solo
# se guarda la referencia al objeto, NUNCA el embedding ni la foto.
MINIO_ENDPOINT = env("MINIO_ENDPOINT", default="http://localhost:9000")
MINIO_ACCESS_KEY = env("MINIO_ACCESS_KEY", default="")
MINIO_SECRET_KEY = env("MINIO_SECRET_KEY", default="")
MINIO_BUCKET_EMBEDDINGS = env("MINIO_BUCKET_EMBEDDINGS", default="luma-face-embeddings")
MINIO_USE_TLS = env.bool("MINIO_USE_TLS", default=False)
# Clave para cifrar los embeddings antes de subirlos (AES-256, 32 bytes b64/hex).
FACE_EMBEDDING_ENCRYPTION_KEY = env("FACE_EMBEDDING_ENCRYPTION_KEY", default="")

# --- Segundo factor (TOTP) ----------------------------------------------
TOTP_ISSUER = env("TOTP_ISSUER", default="Luma Bank")

# --- Politica de intentos de login (HU03) ------------------------------
LOGIN_MAX_FACIAL_ATTEMPTS = env.int("LOGIN_MAX_FACIAL_ATTEMPTS", default=2)
LOGIN_MAX_TOTAL_ATTEMPTS = env.int("LOGIN_MAX_TOTAL_ATTEMPTS", default=5)
ACCOUNT_LOCK_MINUTES = env.int("ACCOUNT_LOCK_MINUTES", default=30)

# --- Reglas de negocio -------------------------------------------------
MIN_SIGNUP_AGE_YEARS = 18

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{asctime} {levelname} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "luma": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}
