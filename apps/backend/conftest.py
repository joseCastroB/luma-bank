"""Configuración global de pytest para el backend.

Objetivo: que NUNCA se llame a LionAPI real (consume créditos reales) y que el
cifrado AES-256 funcione sin depender del entorno de la máquina.

NOTA IMPORTANTE sobre el orden de carga
----------------------------------------
Fijar `os.environ` en el cuerpo del módulo NO alcanza: pytest-django configura
Django (e importa config.settings) durante la carga inicial de plugins, que
ocurre ANTES de que se importe este conftest. Por eso los valores de abajo se
aplican de nuevo sobre el objeto `settings` ya construido, en
`pytest_configure`, que sí corre antes de cualquier test.

Esto no era cosmético: antes, `DNI_VALIDATION_MODE` quedaba en "production"
durante los tests y solo se evitaban llamadas reales porque cada test lo
sobrescribia a mano con el fixture `settings`. Un test nuevo que lo olvidara
habria pegado contra la API de verdad. `test_settings_test_env.py` vigila esto.
"""

import os

# Se dejan en el entorno para el caso de que algo los lea directamente, pero
# la fuente de verdad para los tests es el bloque pytest_configure de abajo.
os.environ.setdefault("DNI_VALIDATION_MODE", "mock")
os.environ.setdefault(
    "FACE_EMBEDDING_ENCRYPTION_KEY",
    "bHVtYS1iYW5rLXRlc3Qta2V5LTMyLWJ5dGVzLW9rISE=",  # "luma-bank-test-key-32-bytes-ok!!"
)
os.environ.setdefault("DJANGO_SECRET_KEY", "test-insecure-key-at-least-32-bytes-long-0000")
os.environ.setdefault("LIONAPI_KEY", "test-lionapi-key")

import pytest  # noqa: E402

# Clave de cifrado de prueba: 32 bytes EXACTOS en base64-urlsafe.
# Debe medir 32 bytes porque crypto._load_key() aborta si no es una clave
# AES-256 valida; una cadena de otra longitud haria que los tests corrieran
# siempre por el camino de error en vez de ejercitar el cifrado real.
_TEST_ENCRYPTION_KEY = "bHVtYS1iYW5rLXRlc3Qta2V5LTMyLWJ5dGVzLW9rISE="


def pytest_configure(config):
    """Aplica sobre `settings` lo que el bloque de os.environ no pudo aplicar."""
    from django.conf import settings

    # Fail-safe de tests: si por lo que sea no se aplicara, los tests pegarian
    # contra LionAPI real. django.setup() ya corrio para cuando estamos aqui.
    settings.DNI_VALIDATION_MODE = "mock"
    settings.FACE_EMBEDDING_ENCRYPTION_KEY = _TEST_ENCRYPTION_KEY
    settings.SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]


@pytest.fixture(autouse=True)
def _locmem_cache(settings):
    """Los tests no dependen de un Valkey real: caché en memoria y limpia."""
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()
