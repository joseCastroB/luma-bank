"""
Red de seguridad del entorno de tests.

Existe por un motivo concreto: el bloque de `os.environ` en `conftest.py` NO
surte efecto, porque pytest-django configura Django (e importa
`config.settings`) antes de importar ese conftest. Durante un tiempo eso paso
desapercibido y `DNI_VALIDATION_MODE` quedaba en "production" mientras el
conftest creia haber puesto "mock". Los tests de registro pasaban unicamente
porque cada uno sobrescribia el valor a mano con el fixture `settings`; un test
nuevo que lo olvidara habria llamado a LionAPI real y quemado creditos.

Estos tests hacen explicito el contrato para que la regresion sea visible.
"""

from django.conf import settings
from django.core.cache import cache

from apps.accounts.services import crypto


def test_dni_validation_is_forced_to_mock():
    """
    LionAPI nunca debe recibir llamadas desde los tests: consume creditos reales.

    Este assert falla ruidosamente si alguien reintroduce un arranque que deje el
    modo en "production".
    """
    assert settings.DNI_VALIDATION_MODE == "mock", (
        "DNI_VALIDATION_MODE debe quedar en 'mock' durante los tests. "
        "Si falla, algún camino está llamando a LionAPI real."
    )


def test_test_environment_uses_in_memory_cache():
    """Los tests no deben depender de un Valkey levantado."""
    assert "locmem" in settings.CACHES["default"]["BACKEND"].lower()
    assert cache is not None


def test_encryption_key_is_a_valid_aes256_key():
    """
    La clave de test debe medir 32 bytes exactos.

    Si no, `crypto._load_key()` aborta y todos los tests de cifrado cairan por el
    camino de error en vez de ejercitar AES de verdad (que era lo que pasaba con
    una clave de otra longitud).
    """
    key = crypto._load_key()
    assert len(key) == 32
    assert settings.FACE_EMBEDDING_ENCRYPTION_KEY
