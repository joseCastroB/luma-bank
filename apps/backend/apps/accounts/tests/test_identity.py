"""HU02 - validación de identidad por DNI (RENIEC vía LionAPI / mock)."""

import pytest
import responses
from django.core.cache import cache

from apps.accounts.services.identity import (
    IdentityNotFound,
    IdentityServiceError,
    InvalidDni,
    normalize_dni,
    validate_dni,
)


class TestNormalizeDni:
    def test_trims_surrounding_whitespace(self):
        # Bug real: un espacio invisible al copiar el número rompía la validación.
        assert normalize_dni("  12345678  ") == "12345678"
        assert normalize_dni("\t12345678\n") == "12345678"

    @pytest.mark.parametrize("bad", ["1234567", "123456789", "1234567a", "", "  ", "abcdefgh"])
    def test_rejects_non_8_digits(self, bad):
        with pytest.raises(InvalidDni):
            normalize_dni(bad)


@pytest.mark.django_db
class TestValidateDniMock:
    def test_mock_returns_names_without_http(self, settings):
        settings.DNI_VALIDATION_MODE = "mock"
        data = validate_dni(" 00000001 ")
        assert data.dni == "00000001"
        assert data.nombres and data.apellido_paterno
        assert data.source == "mock"

    def test_mock_is_deterministic(self, settings):
        settings.DNI_VALIDATION_MODE = "mock"
        assert validate_dni("42424242").nombre_completo == validate_dni("42424242").nombre_completo


@pytest.mark.django_db
class TestValidateDniProduction:
    @responses.activate
    def test_calls_lionapi_and_caches(self, settings):
        settings.DNI_VALIDATION_MODE = "production"
        settings.LIONAPI_KEY = "k"
        settings.LIONAPI_BASE_URL = "https://api.test/v1"
        responses.add(
            responses.GET,
            "https://api.test/v1/consulta-dni/70123456",
            json={
                "data": {
                    "nombres": "MARIA",
                    "apellido_paterno": "PEREZ",
                    "apellido_materno": "GOMEZ",
                }
            },
            status=200,
        )
        first = validate_dni("70123456")
        assert first.nombres == "MARIA"
        assert first.source == "lionapi"
        assert cache.get("identity:dni:70123456") is not None

        # Segunda llamada: desde caché, sin nuevo HTTP.
        second = validate_dni("70123456")
        assert second.source == "cache"
        assert len(responses.calls) == 1

    @responses.activate
    def test_not_found_raises(self, settings):
        settings.DNI_VALIDATION_MODE = "production"
        settings.LIONAPI_KEY = "k"
        settings.LIONAPI_BASE_URL = "https://api.test/v1"
        responses.add(responses.GET, "https://api.test/v1/consulta-dni/99999999", status=404)
        with pytest.raises(IdentityNotFound):
            validate_dni("99999999")

    @responses.activate
    def test_service_error_raises(self, settings):
        settings.DNI_VALIDATION_MODE = "production"
        settings.LIONAPI_KEY = "k"
        settings.LIONAPI_BASE_URL = "https://api.test/v1"
        responses.add(responses.GET, "https://api.test/v1/consulta-dni/70123456", status=500)
        with pytest.raises(IdentityServiceError):
            validate_dni("70123456")
