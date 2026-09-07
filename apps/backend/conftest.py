"""Configuración global de pytest para el backend.

Fija variables de entorno seguras ANTES de que Django cargue:
- DNI_VALIDATION_MODE=mock  -> nunca se llama a LionAPI (consume créditos reales)
- clave de cifrado de prueba -> el cifrado AES funciona sin depender del entorno
"""

import os

os.environ.setdefault("DNI_VALIDATION_MODE", "mock")
os.environ.setdefault(
    "FACE_EMBEDDING_ENCRYPTION_KEY",
    "dGVzdC1rZXktMzItYnl0ZXMtZm9yLXVuaXQtdGVzdHMtLS0=",  # cualquier string sirve (SHA-256)
)
os.environ.setdefault("DJANGO_SECRET_KEY", "test-insecure-key")
os.environ.setdefault("LIONAPI_KEY", "test-lionapi-key")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _locmem_cache(settings):
    """Los tests no dependen de un Valkey real: caché en memoria y limpia."""
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()
