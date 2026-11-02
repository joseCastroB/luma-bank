"""Bloqueo y desbloqueo de cuenta, avisos por correo y actualización del rostro."""

from datetime import date, timedelta
from smtplib import SMTPException

import pyotp
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog, FaceEmbedding, LoginAttempt
from apps.accounts.services import crypto, face_store, registration, security_mail

User = get_user_model()

ROSTRO = [round(0.01 * i - 0.5, 4) for i in range(128)]
LEJANO = [x + 1.0 for x in ROSTRO]
ROSTRO_NUEVO = [round(0.02 * i - 1.0, 4) for i in range(128)]
VIVACIDAD = {"passed": True, "checks": ["blink", "head_turn"]}


@pytest.fixture
def almacen(monkeypatch):
    """MinIO simulado en memoria."""
    store: dict[tuple[str, str], bytes] = {}
    contador = {"n": 0}

    def put(user_id, ciphertext):
        contador["n"] += 1
        key = f"embeddings/{user_id}/{contador['n']}.bin"
        store[("bucket", key)] = ciphertext
        return "bucket", key

    monkeypatch.setattr(face_store, "put_embedding", put)
    monkeypatch.setattr(face_store, "get_embedding", lambda b, k: store[(b, k)])
    monkeypatch.setattr(face_store, "delete_embedding", lambda b, k: store.pop((b, k), None))
    return store


@pytest.fixture
def registro(db, almacen, settings):
    settings.DNI_VALIDATION_MODE = "mock"
    return registration.register_customer(
        dni="70000001",
        birth_date=date(2000, 1, 1),
        email="cliente@example.com",
        password="Clave-Segura-2026",
        face_descriptor=ROSTRO,
        descriptor_algorithm="test",
    )


@pytest.fixture
def api(registro):
    client = APIClient()
    client.force_authenticate(registro.user)
    return client


def _login_facial(client, descriptor):
    return client.post(
        reverse("accounts:login-facial"),
        {"identifier": "cliente@example.com", "face_descriptor": descriptor, "liveness": VIVACIDAD},
        format="json",
    )


def _bloquear(registro):
    client = APIClient()
    for _ in range(5):
        _login_facial(client, LEJANO)
    registro.user.refresh_from_db()
    assert registro.user.locked_until is not None
    return registro.user


def _actualizar(api, registro, *, totp=None, liveness=VIVACIDAD, descriptor=ROSTRO_NUEVO):
    return api.post(
        reverse("accounts:biometrics"),
        {
            "totp": pyotp.TOTP(registro.totp_secret).now() if totp is None else totp,
            "liveness": liveness,
            "face_descriptor": descriptor,
            "descriptor_algorithm": "nuevo-modelo",
        },
        format="json",
    )


@pytest.mark.django_db
class TestAvisoDeBloqueo:
    def test_el_quinto_fallo_bloquea_30_minutos_y_avisa(self, registro):
        mail.outbox.clear()
        user = _bloquear(registro)
        restante = user.locked_until - timezone.now()
        assert timedelta(minutes=29) < restante <= timedelta(minutes=30)

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["cliente@example.com"]
        assert "Bloqueamos" in mail.outbox[0].subject
        assert "intentos fallidos" in mail.outbox[0].body

    def test_insistir_con_la_cuenta_bloqueada_no_reenvia(self, registro):
        _bloquear(registro)
        mail.outbox.clear()
        assert _login_facial(APIClient(), LEJANO).status_code == 423
        assert mail.outbox == []

    def test_el_correo_no_lleva_datos_sensibles(self, registro):
        mail.outbox.clear()
        _bloquear(registro)
        assert registro.user.dni not in mail.outbox[0].body

    def test_si_falla_el_correo_igual_bloquea(self, registro, monkeypatch):
        def falla(*args, **kwargs):
            raise SMTPException("sin servidor")

        monkeypatch.setattr(security_mail, "send_mail", falla)
        user = _bloquear(registro)
        assert user.locked_until is not None

    def test_el_bloqueo_queda_en_la_auditoria(self, registro):
        user = _bloquear(registro)
        log = AuditLog.objects.get(action="account.lock")
        assert log.user == user
        assert log.entity_id == str(user.pk)


@pytest.mark.django_db
class TestDesbloqueoPorAdministrador:
    @pytest.fixture(autouse=True)
    def _estaticos_sin_manifiesto(self, settings):
        """Las pruebas no corren collectstatic y el admin pide sus estáticos."""
        settings.STORAGES = {
            **settings.STORAGES,
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }

    @pytest.fixture
    def admin_client(self, client):
        admin = User.objects.create_superuser(
            username="admin@example.com", email="admin@example.com", password="Clave-Segura-2026"
        )
        client.force_login(admin)
        client.admin_user = admin
        return client

    def _accion(self, client, *usuarios):
        return client.post(
            reverse("admin:accounts_user_changelist"),
            {"action": "desbloquear_cuentas", "_selected_action": [u.pk for u in usuarios]},
            follow=True,
        )

    def test_desbloquea_y_reinicia_los_intentos(self, admin_client, registro):
        user = _bloquear(registro)
        assert self._accion(admin_client, user).status_code == 200
        user.refresh_from_db()
        assert user.locked_until is None
        assert user.failed_login_attempts == 0
        assert user.failed_facial_attempts == 0
        # Y el cliente vuelve a entrar.
        assert _login_facial(APIClient(), ROSTRO).status_code == 200

    def test_deja_registro_de_auditoria(self, admin_client, registro):
        user = _bloquear(registro)
        self._accion(admin_client, user)
        log = AuditLog.objects.get(action="account.unlock")
        assert log.user == admin_client.admin_user
        assert log.entity == "usuario"
        assert log.entity_id == str(user.pk)
        assert log.ip_address

    def test_ignora_cuentas_que_no_estan_bloqueadas(self, admin_client, registro):
        self._accion(admin_client, registro.user)
        assert not AuditLog.objects.filter(action="account.unlock").exists()

    def test_no_se_puede_desbloquear_editando_el_formulario(self, admin_client, registro):
        """Sin la acción no habría auditoría: los campos de bloqueo son de solo lectura."""
        user = _bloquear(registro)
        resp = admin_client.get(reverse("admin:accounts_user_change", args=[user.pk]))
        assert b'name="locked_until' not in resp.content

    def test_personal_sin_permiso_no_puede(self, client, registro):
        user = _bloquear(registro)
        staff = User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="Clave-Segura-2026",
            is_staff=True,
        )
        client.force_login(staff)
        self._accion(client, user)
        user.refresh_from_db()
        assert user.locked_until is not None

    def test_la_bitacora_no_se_puede_modificar_desde_el_admin(self, admin_client, registro):
        _bloquear(registro)
        log = AuditLog.objects.get(action="account.lock")
        assert admin_client.get(reverse("admin:accounts_auditlog_changelist")).status_code == 200
        borrar = reverse("admin:accounts_auditlog_delete", args=[log.pk])
        assert admin_client.post(borrar, {"post": "yes"}).status_code == 403
        assert AuditLog.objects.filter(pk=log.pk).exists()
        assert admin_client.get(reverse("admin:accounts_auditlog_add")).status_code == 403


@pytest.mark.django_db
class TestActualizacionDeRostro:
    def test_el_rostro_nuevo_reemplaza_al_anterior(self, api, registro, almacen):
        anterior = FaceEmbedding.objects.get(user=registro.user)
        resp = _actualizar(api, registro)
        assert resp.status_code == 200, resp.content

        actual = FaceEmbedding.objects.get(user=registro.user)
        assert actual.object_key != anterior.object_key
        assert actual.algorithm == "nuevo-modelo"
        assert list(almacen) == [("bucket", actual.object_key)]
        cliente = APIClient()
        assert _login_facial(cliente, ROSTRO_NUEVO).status_code == 200
        assert _login_facial(cliente, ROSTRO).status_code == 401

    def test_guarda_el_vector_cifrado(self, api, registro, almacen):
        _actualizar(api, registro)
        actual = FaceEmbedding.objects.get(user=registro.user)
        blob = almacen[("bucket", actual.object_key)]
        descifrado = crypto.decrypt_embedding(blob)
        assert descifrado == pytest.approx(ROSTRO_NUEVO, abs=1e-5)

    def test_registra_fecha_y_hora_en_auditoria(self, api, registro):
        _actualizar(api, registro)
        log = AuditLog.objects.get(action="biometrics.update")
        assert log.user == registro.user
        assert log.created_at is not None
        assert log.metadata == {"algorithm": "nuevo-modelo"}

    def test_avisa_por_correo(self, api, registro):
        mail.outbox.clear()
        _actualizar(api, registro)
        assert len(mail.outbox) == 1
        assert "rostro" in mail.outbox[0].subject

    def test_exige_la_prueba_de_vida(self, api, registro, almacen):
        anterior = FaceEmbedding.objects.get(user=registro.user).object_key
        resp = _actualizar(api, registro, liveness={"passed": False, "checks": []})
        assert resp.status_code == 400
        assert FaceEmbedding.objects.get(user=registro.user).object_key == anterior
        assert not AuditLog.objects.filter(action="biometrics.update").exists()

    def test_sin_prueba_de_vida_no_procesa(self, api, registro):
        resp = api.post(
            reverse("accounts:biometrics"),
            {"totp": "123456", "face_descriptor": ROSTRO_NUEVO},
            format="json",
        )
        assert resp.status_code == 400

    def test_exige_el_codigo_totp(self, api, registro):
        anterior = FaceEmbedding.objects.get(user=registro.user).object_key
        resp = _actualizar(api, registro, totp="000000")
        assert resp.status_code == 403
        assert resp.json()["code"] == "totp_invalid"
        assert FaceEmbedding.objects.get(user=registro.user).object_key == anterior

    def test_cinco_codigos_incorrectos_bloquean(self, api, registro):
        for _ in range(4):
            _actualizar(api, registro, totp="000000")
        assert _actualizar(api, registro, totp="000000").status_code == 423
        registro.user.refresh_from_db()
        assert registro.user.locked_until is not None

    def test_con_la_cuenta_bloqueada_no_actualiza(self, api, registro):
        _bloquear(registro)
        api.force_authenticate(User.objects.get(pk=registro.user.pk))
        assert _actualizar(api, registro).status_code == 423

    def test_rechaza_un_descriptor_invalido(self, api, registro):
        assert _actualizar(api, registro, descriptor=[0.1, 0.2]).status_code == 400

    def test_requiere_autenticacion(self, registro):
        resp = APIClient().post(reverse("accounts:biometrics"), {}, format="json")
        assert resp.status_code == 401

    def test_si_falla_la_base_de_datos_conserva_el_rostro(
        self, api, registro, almacen, monkeypatch
    ):
        anterior = FaceEmbedding.objects.get(user=registro.user).object_key
        cantidad = len(almacen)

        def falla(*args, **kwargs):
            raise RuntimeError("fallo de auditoría")

        monkeypatch.setattr("apps.accounts.services.audit.record", falla)
        api.raise_request_exception = False
        assert _actualizar(api, registro).status_code == 500
        assert FaceEmbedding.objects.get(user=registro.user).object_key == anterior
        # El objeto nuevo no queda huérfano y el anterior sigue en su lugar.
        assert len(almacen) == cantidad
        assert ("bucket", anterior) in almacen

    def test_el_perfil_muestra_la_ultima_actualizacion(self, api, registro):
        _actualizar(api, registro)
        body = api.get(reverse("accounts:me")).json()
        assert body["has_totp"] is True
        assert body["face_updated_at"]


@pytest.mark.django_db
class TestIpInvalida:
    def test_una_ip_falsa_no_rompe_el_login(self, registro):
        resp = APIClient().post(
            reverse("accounts:login-facial"),
            {"identifier": "cliente@example.com", "face_descriptor": ROSTRO, "liveness": VIVACIDAD},
            format="json",
            HTTP_X_FORWARDED_FOR="esto-no-es-una-ip",
        )
        assert resp.status_code == 200
        assert LoginAttempt.objects.get().ip_address is None
