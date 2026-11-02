"""
Pruebas de seguridad web (APF2, capítulo C.3).

Cubren los riesgos pedidos por la rúbrica: CORS, XSS e inyección SQL, además
del control de acceso de la API. Se ejecutan con el resto de la suite:

    docker compose run --rm backend pytest apps/accounts/tests/test_security.py -v
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

ORIGEN_PERMITIDO = "https://luma-bank.example"
ORIGEN_MALICIOSO = "https://sitio-malicioso.example"

PAYLOADS_SQLI = [
    "' OR '1'='1",
    "admin@example.com' --",
    "'; DROP TABLE usuario; --",
    "1 UNION SELECT clave FROM usuario",
]
PAYLOAD_XSS = "<script>alert('xss')</script>"


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def cors_estricto(settings):
    """Misma política que producción: solo el origen del frontend."""
    settings.CORS_ALLOW_ALL_ORIGINS = False
    settings.CORS_ALLOWED_ORIGINS = [ORIGEN_PERMITIDO]


@pytest.fixture
def victima(db):
    return User.objects.create_user(
        username="victima@example.com",
        email="victima@example.com",
        password="Clave-Segura-2026",
    )


@pytest.mark.django_db
class TestCors:
    def test_origen_no_autorizado_no_recibe_cabecera(self, client, cors_estricto):
        resp = client.get(reverse("health"), HTTP_ORIGIN=ORIGEN_MALICIOSO)
        assert "Access-Control-Allow-Origin" not in resp.headers

    def test_origen_autorizado_recibe_cabecera(self, client, cors_estricto):
        resp = client.get(reverse("health"), HTTP_ORIGIN=ORIGEN_PERMITIDO)
        assert resp.headers["Access-Control-Allow-Origin"] == ORIGEN_PERMITIDO

    def test_preflight_de_origen_no_autorizado_es_rechazado(self, client, cors_estricto):
        resp = client.options(
            reverse("accounts:login-password"),
            HTTP_ORIGIN=ORIGEN_MALICIOSO,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        assert "Access-Control-Allow-Origin" not in resp.headers


@pytest.mark.django_db
class TestInyeccionSql:
    @pytest.mark.parametrize("payload", PAYLOADS_SQLI)
    def test_login_no_se_puede_saltar_con_sqli(self, client, victima, payload):
        resp = client.post(
            reverse("accounts:login-password"),
            {"identifier": payload, "password": payload, "totp": "000000"},
            format="json",
        )
        assert resp.status_code in (400, 401)
        assert "access" not in resp.json()
        # La tabla de usuarios sigue intacta: el payload se trató como dato.
        assert User.objects.filter(email="victima@example.com").count() == 1

    @pytest.mark.parametrize("payload", PAYLOADS_SQLI)
    def test_validar_dni_rechaza_sqli(self, client, payload):
        resp = client.post(reverse("accounts:validar-dni"), {"dni": payload}, format="json")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestXss:
    def test_payload_no_se_refleja_en_la_respuesta(self, client):
        resp = client.post(
            reverse("accounts:login-password"),
            {"identifier": PAYLOAD_XSS, "password": "x", "totp": "000000"},
            format="json",
        )
        assert resp["Content-Type"].startswith("application/json")
        assert PAYLOAD_XSS not in resp.content.decode()

    def test_dni_con_script_es_rechazado_como_json(self, client):
        resp = client.post(reverse("accounts:validar-dni"), {"dni": PAYLOAD_XSS}, format="json")
        assert resp.status_code == 400
        assert resp["Content-Type"].startswith("application/json")
        assert PAYLOAD_XSS not in resp.content.decode()

    def test_cabeceras_de_proteccion_del_navegador(self, client):
        resp = client.get(reverse("health"))
        assert resp["X-Content-Type-Options"] == "nosniff"
        assert resp["X-Frame-Options"] in ("DENY", "SAMEORIGIN")


@pytest.mark.django_db
class TestControlDeAcceso:
    def test_no_se_emite_jwt_solo_con_contrasena(self, client, victima):
        resp = client.post(
            "/api/v1/auth/token/",
            {"username": "victima@example.com", "password": "Clave-Segura-2026"},
            format="json",
        )
        assert resp.status_code == 404

    def test_recurso_privado_sin_token(self, client):
        assert client.get(reverse("accounts:me")).status_code == 401

    def test_token_mal_formado(self, client):
        client.credentials(HTTP_AUTHORIZATION="Bearer esto.no.es-un-jwt")
        assert client.get(reverse("accounts:me")).status_code == 401

    def test_token_firmado_con_otra_clave(self, client, victima):
        falso = jwt.encode(
            {
                "token_type": "access",
                "user_id": victima.pk,
                "jti": "forjado",
                "exp": datetime.now(UTC) + timedelta(minutes=5),
            },
            "clave-del-atacante",
            algorithm="HS256",
        )
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {falso}")
        assert client.get(reverse("accounts:me")).status_code == 401

    def test_login_no_revela_si_el_usuario_existe(self, client, victima):
        url = reverse("accounts:login-password")
        existe = client.post(
            url,
            {"identifier": "victima@example.com", "password": "mala", "totp": "000000"},
            format="json",
        )
        no_existe = client.post(
            url,
            {"identifier": "nadie@example.com", "password": "mala", "totp": "000000"},
            format="json",
        )
        assert existe.status_code == no_existe.status_code == 401
        assert existe.json()["detail"] == no_existe.json()["detail"]
