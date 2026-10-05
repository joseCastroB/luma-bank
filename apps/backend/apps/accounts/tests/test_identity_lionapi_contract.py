"""
Contrato de LionAPI (Software Lion) contra respuestas REALES de la API.

Estas formas de sobre se copiaron de consultas hechas a
GET https://www.softwarelion.pe/api/lion-api/v1/consulta-dni/:dni
con el header `x-api-key`. No son inventadas: reproducen lo que devolvio el
servidor, incluidos sus errores.

El detalle que mas importa: la API responde HTTP 200 incluso cuando el DNI no
existe. Por eso el status HTTP NO decide nada y hay que leer el campo `success`.
"""

from unittest.mock import Mock, patch

import pytest

from apps.accounts.services.identity import (
    IdentityNotFound,
    IdentityServiceError,
    _parse_lionapi,
)


def _resp(payload, status=200):
    r = Mock()
    r.status_code = status
    r.json.return_value = payload
    r.text = str(payload)
    return r


class TestParseLionApiRealContract:
    def test_exito_real_desempaqueta_el_sobre(self):
        payload = {
            "success": True,
            "message": "exito",
            "result": {
                "dni": "45678912",
                "paterno": "LANCHO",
                "materno": "ALVAREZ",
                "nombres": "ANA VANESA",
                "sexo": "F",
                "codigo_verificacion": "4",
            },
        }
        data = _parse_lionapi("45678912", payload)
        assert data.nombres == "ANA VANESA"
        assert data.apellidos == "LANCHO ALVAREZ"
        assert data.dni == "45678912"
        assert data.source == "lionapi"

    def test_dni_inexistente_llega_con_http_200_y_success_false(self):
        # Este es el caso peligroso: si el codigo solo mirara el status HTTP,
        # un DNI inexistente pasaria por validado.
        payload = {"success": False, "message": "DNI no encontrado", "result": None}
        with pytest.raises(IdentityNotFound):
            _parse_lionapi("12345678", payload)

    def test_fallo_del_servidor_no_se_confunde_con_dni_inexistente(self):
        # Bug real observado en la API: responde success=false con un error de
        # su propio codigo. Decirle al usuario "DNI no encontrado" seria falso.
        payload = {
            "success": False,
            "message": "catch: persona.codigo_verificacion.trim is not a function",
            "result": None,
        }
        with pytest.raises(IdentityServiceError):
            _parse_lionapi("70111222", payload)

    def test_dni_corto_que_real_responde_con_200(self):
        payload = {
            "success": False,
            "message": "El dni debe tener una longitud de 8 dígitos",
            "result": None,
        }
        with pytest.raises(IdentityServiceError):
            _parse_lionapi("7011122", payload)

    def test_result_vacio_sin_mensaje_es_error_de_servicio(self):
        with pytest.raises(IdentityServiceError):
            _parse_lionapi("70111222", {"success": False, "message": "", "result": None})


class TestLionApiLookupStatusCodes:
    @pytest.fixture(autouse=True)
    def _api_key(self, settings):
        # El cliente aborta sin key, y los tests corren en modo mock sin
        # key real. Estos tests verifican el transporte HTTP, asi que se
        # inyecta una key ficticia para llegar hasta el requests.get.
        settings.LIONAPI_KEY = "ls_live_ficticia_para_tests"

    @patch("apps.accounts.services.identity.requests.get")
    def test_401_es_problema_de_despliegue(self, mock_get):
        mock_get.return_value = _resp({"message": "Falta la API Key"}, status=401)
        with pytest.raises(IdentityServiceError):
            from apps.accounts.services.identity import _lionapi_lookup

            _lionapi_lookup("45678912")

    @patch("apps.accounts.services.identity.requests.get")
    def test_429_es_agotamiento_de_creditos(self, mock_get):
        from apps.accounts.services.identity import LionApiQuotaExceeded, _lionapi_lookup

        mock_get.return_value = _resp({"message": "Limite alcanzado"}, status=429)
        with pytest.raises(LionApiQuotaExceeded):
            _lionapi_lookup("45678912")

    @patch("apps.accounts.services.identity.requests.get")
    def test_envia_el_header_exacto_que_exige_la_api(self, mock_get):
        from apps.accounts.services.identity import _lionapi_lookup

        mock_get.return_value = _resp(
            {
                "success": True,
                "message": "exito",
                "result": {
                    "dni": "45678912",
                    "paterno": "LANCHO",
                    "materno": "ALVAREZ",
                    "nombres": "ANA VANESA",
                },
            }
        )
        _lionapi_lookup("45678912")
        _, kwargs = mock_get.call_args
        assert "x-api-key" in kwargs["headers"]
        assert kwargs["timeout"] == 10

    @patch("apps.accounts.services.identity.requests.get")
    def test_timeout_de_red_es_error_de_servicio(self, mock_get):
        import requests

        from apps.accounts.services.identity import _lionapi_lookup

        mock_get.side_effect = requests.Timeout("caido")
        with pytest.raises(IdentityServiceError):
            _lionapi_lookup("45678912")

    @patch("apps.accounts.services.identity.requests.get")
    def test_json_invalido_es_error_de_servicio(self, mock_get):
        from apps.accounts.services.identity import _lionapi_lookup

        r = Mock()
        r.status_code = 200
        r.json.side_effect = ValueError("no es json")
        mock_get.return_value = r
        with pytest.raises(IdentityServiceError):
            _lionapi_lookup("45678912")
