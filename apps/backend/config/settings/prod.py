"""Settings de produccion. Se activa con DJANGO_SETTINGS_MODULE=config.settings.prod."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import DNI_VALIDATION_MODE, env

DEBUG = False

# ALLOWED_HOSTS es obligatorio en produccion.
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# SECRET_KEY no puede quedarse en el valor por defecto.
SECRET_KEY = env("DJANGO_SECRET_KEY")
if SECRET_KEY == "insecure-dev-key-change-me":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY debe definirse en produccion.")

# ---------------------------------------------------------------------------
# GUARDIA FAIL-SAFE: la validacion de DNI JAMAS puede correr en modo 'mock'
# en produccion. Esto es defensa en profundidad ademas del check de CI/CD
# (scripts/check_dni_validation_mode.sh).
# ---------------------------------------------------------------------------
if DNI_VALIDATION_MODE != "production":
    raise ImproperlyConfigured(
        "DNI_VALIDATION_MODE debe ser 'production' cuando se usa "
        f"config.settings.prod (valor actual: {DNI_VALIDATION_MODE!r}). "
        "El modo 'mock' esta prohibido en produccion."
    )

# ---------------------------------------------------------------------------
# Endurecimiento HTTP (OWASP ASVS L2)
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
