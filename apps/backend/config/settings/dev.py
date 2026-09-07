"""Settings de desarrollo. NO usar en produccion."""

from .base import *  # noqa: F403
from .base import REST_FRAMEWORK

DEBUG = True

ALLOWED_HOSTS = ["*"]

# En dev permitimos cualquier origen local para agilizar el trabajo del equipo.
CORS_ALLOW_ALL_ORIGINS = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Navegable en el browser al desarrollar la API.
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
