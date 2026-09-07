"""Settings de desarrollo. NO usar en produccion."""

from .base import *  # noqa: F403
from .base import CSRF_TRUSTED_ORIGINS, REST_FRAMEWORK

DEBUG = True

ALLOWED_HOSTS = ["*"]

# En dev permitimos cualquier origen local para agilizar el trabajo del equipo.
CORS_ALLOW_ALL_ORIGINS = True

# Confiar en los orígenes locales para CSRF (p. ej. si hay una sesión de admin
# abierta en el mismo navegador que el SPA).
CSRF_TRUSTED_ORIGINS = list(
    {
        *CSRF_TRUSTED_ORIGINS,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    }
)

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Navegable en el browser al desarrollar la API.
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
