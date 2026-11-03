"""
Integración con los servicios reales. No corren con el `pytest` normal:

    docker compose exec backend pytest -m integracion -v
    docker compose exec backend pytest -m externo -v

`integracion` usa MinIO, Valkey y un servidor SMTP local. `externo` consulta a SUNAT
por internet, así que un fallo puede ser del proveedor. LionAPI queda fuera a propósito:
cada consulta consume créditos reales.
"""

import email
import socket
import time
import uuid
from datetime import date, timedelta
from email.header import decode_header, make_header
from types import SimpleNamespace

import pytest
import requests
from aiosmtpd.controller import Controller
from botocore.exceptions import ClientError
from django.conf import settings as django_settings
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework.test import APIClient

from apps.accounts.models import FaceEmbedding
from apps.accounts.services import crypto, face_store, identity, security_mail
from apps.banking import exchange_rates
from apps.banking.models import ExchangeRate

DESCRIPTOR = [round(0.01 * i - 0.6, 4) for i in range(128)]
CLAVE = "Clave-Segura-2026"


def _clave_cache() -> str:
    return f"integracion:{uuid.uuid4().hex}"


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def bucket(settings):
    """Un bucket propio para cada prueba: nunca toca los embeddings del entorno."""
    nombre = f"luma-integracion-{uuid.uuid4().hex[:12]}"
    settings.MINIO_BUCKET_EMBEDDINGS = nombre
    yield nombre
    cliente = face_store._client()
    for objeto in cliente.list_objects_v2(Bucket=nombre).get("Contents", []):
        cliente.delete_object(Bucket=nombre, Key=objeto["Key"])
    cliente.delete_bucket(Bucket=nombre)


@pytest.mark.integracion
class TestMinioReal:
    def test_guarda_lee_y_borra_un_objeto(self, bucket):
        nombre, clave = face_store.put_embedding(1, b"contenido cifrado")
        assert nombre == bucket
        assert face_store.get_embedding(nombre, clave) == b"contenido cifrado"

        face_store.delete_embedding(nombre, clave)
        with pytest.raises(ClientError):
            face_store.get_embedding(nombre, clave)

    def test_el_vector_se_guarda_cifrado_y_se_recupera_igual(self, bucket):
        cifrado = crypto.encrypt_embedding(DESCRIPTOR)
        nombre, clave = face_store.put_embedding(1, cifrado)

        guardado = face_store.get_embedding(nombre, clave)
        assert str(DESCRIPTOR[0]).encode() not in guardado
        assert crypto.decrypt_embedding(guardado) == pytest.approx(DESCRIPTOR)

    def test_un_objeto_inexistente_da_error(self, bucket):
        face_store.put_embedding(1, b"x")
        with pytest.raises(ClientError):
            face_store.get_embedding(bucket, "embeddings/no-existe.bin")

    def test_credenciales_incorrectas_se_rechazan(self, settings):
        settings.MINIO_BUCKET_EMBEDDINGS = f"luma-integracion-{uuid.uuid4().hex[:12]}"
        settings.MINIO_SECRET_KEY = "clave-incorrecta"
        with pytest.raises(ClientError):
            face_store.put_embedding(1, b"x")

    @pytest.mark.django_db
    def test_registro_y_login_facial_usan_el_objeto_guardado(self, bucket, settings):
        settings.DNI_VALIDATION_MODE = "mock"
        dni = f"7{uuid.uuid4().int % 10_000_000:07d}"
        correo = f"{uuid.uuid4().hex[:12]}@lumabank.test"
        cliente = APIClient()
        try:
            registro = cliente.post(
                reverse("accounts:registro"),
                {
                    "dni": dni,
                    "identity_confirmed": True,
                    "birth_date": (date.today() - timedelta(days=365 * 25)).isoformat(),
                    "email": correo,
                    "password": CLAVE,
                    "liveness": {"passed": True, "checks": ["blink", "turn_left"]},
                    "face_descriptor": DESCRIPTOR,
                    "descriptor_algorithm": "face-api ssdMobilenetv1 128d",
                },
                format="json",
            )
            assert registro.status_code == 201, registro.content

            referencia = FaceEmbedding.objects.get(user__email=correo)
            assert referencia.bucket == bucket
            assert face_store.get_embedding(referencia.bucket, referencia.object_key)

            login = cliente.post(
                reverse("accounts:login-facial"),
                {
                    "identifier": correo,
                    "face_descriptor": DESCRIPTOR,
                    "liveness": {"passed": True, "checks": ["blink"]},
                },
                format="json",
            )
            assert login.status_code == 200, login.content
            assert login.json()["access"]
        finally:
            cache.delete(identity._CACHE_PREFIX + dni)


@pytest.mark.integracion
class TestValkeyReal:
    def test_es_el_servicio_real(self):
        assert "RedisCache" in django_settings.CACHES["default"]["BACKEND"]
        assert cache._cache.get_client().ping() is True

    def test_guarda_lee_y_borra(self):
        clave = _clave_cache()
        cache.set(clave, {"saldo": "10.00"}, timeout=30)
        assert cache.get(clave) == {"saldo": "10.00"}

        cache.delete(clave)
        assert cache.get(clave) is None

    def test_respeta_el_vencimiento(self):
        clave = _clave_cache()
        cache.set(clave, "valor", timeout=1)
        time.sleep(1.2)
        assert cache.get(clave) is None

    def test_add_sirve_de_bloqueo(self):
        """Así limita exchange_rates las consultas a SUNAT a una por hora."""
        clave = _clave_cache()
        try:
            assert cache.add(clave, 1, 30) is True
            assert cache.add(clave, 1, 30) is False
        finally:
            cache.delete(clave)

    def test_la_identidad_queda_en_cache(self, settings):
        settings.DNI_VALIDATION_MODE = "mock"
        dni = f"7{uuid.uuid4().int % 10_000_000:07d}"
        try:
            assert identity.validate_dni(dni).source == "mock"
            assert identity.validate_dni(dni).source == "cache"
        finally:
            cache.delete(identity._CACHE_PREFIX + dni)

    def test_sin_servicio_da_error_de_conexion(self, settings):
        settings.CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": f"redis://127.0.0.1:{_puerto_libre()}/0",
            }
        }
        with pytest.raises(RedisConnectionError):
            cache.get(_clave_cache())

    @pytest.mark.django_db
    def test_sin_servicio_el_estado_lo_informa(self, settings):
        settings.CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": f"redis://127.0.0.1:{_puerto_libre()}/0",
            }
        }
        respuesta = APIClient().get(reverse("health"))
        assert respuesta.status_code == 503
        assert respuesta.json()["status"] == "degraded"


@pytest.fixture
def smtp(settings):
    """Servidor SMTP local: el correo viaja por el protocolo real, sin salir del equipo."""
    mensajes = []

    class Receptor:
        codigo = "250 OK"

        async def handle_DATA(self, server, session, envelope):
            if self.codigo.startswith("250"):
                mensajes.append(envelope)
            return self.codigo

    receptor = Receptor()
    puerto = _puerto_libre()
    servidor = Controller(receptor, hostname="127.0.0.1", port=puerto)
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "127.0.0.1"
    settings.EMAIL_PORT = puerto
    settings.EMAIL_USE_TLS = False
    settings.EMAIL_HOST_USER = ""
    settings.EMAIL_HOST_PASSWORD = ""
    servidor.start()
    yield SimpleNamespace(mensajes=mensajes, receptor=receptor)
    servidor.stop()


def _cliente_bloqueado():
    return SimpleNamespace(
        pk=1,
        email="cliente@lumabank.test",
        first_name="Ana",
        locked_until=timezone.now() + timedelta(minutes=30),
    )


@pytest.mark.integracion
class TestSmtpReal:
    def test_el_aviso_de_bloqueo_llega_por_smtp(self, smtp):
        security_mail.notify_account_locked(_cliente_bloqueado())

        [recibido] = smtp.mensajes
        assert recibido.rcpt_tos == ["cliente@lumabank.test"]
        mensaje = email.message_from_bytes(recibido.content)
        assert str(make_header(decode_header(mensaje["Subject"]))).startswith("Bloqueamos")

    def test_un_rechazo_del_servidor_no_interrumpe_la_operacion(self, smtp):
        smtp.receptor.codigo = "550 Rechazado"
        security_mail.notify_account_locked(_cliente_bloqueado())
        assert smtp.mensajes == []

    def test_un_servidor_caido_no_interrumpe_la_operacion(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
        settings.EMAIL_HOST = "127.0.0.1"
        settings.EMAIL_PORT = _puerto_libre()
        settings.EMAIL_USE_TLS = False
        security_mail.notify_account_locked(_cliente_bloqueado())


@pytest.mark.externo
class TestSunatEnVivo:
    def test_publica_en_el_formato_esperado(self):
        respuesta = requests.get(django_settings.EXCHANGE_RATE_URL, timeout=20)
        assert respuesta.status_code == 200

        fecha, compra, venta = exchange_rates._parse(respuesta.text)
        assert timezone.localdate() - fecha <= timedelta(
            days=django_settings.EXCHANGE_RATE_MAX_AGE_DAYS
        )
        assert 0 < compra <= venta

    @pytest.mark.django_db
    def test_el_sistema_guarda_lo_publicado(self):
        exchange_rates.refresh_rate()
        tipo = ExchangeRate.objects.get()
        assert tipo.source == "SUNAT"
        assert tipo.buy <= tipo.sell
