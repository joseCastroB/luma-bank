"""HU02 - endpoints de registro / apertura de cuenta."""

from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import FaceEmbedding
from apps.accounts.services import face_store
from apps.banking.models import Account

User = get_user_model()

VALID_DESCRIPTOR = [round(0.01 * i - 0.6, 4) for i in range(128)]


@pytest.fixture(autouse=True)
def _fake_minio(monkeypatch):
    """No tocar MinIO en los tests: se simula la subida del objeto."""
    calls = []

    def fake_put(user_id, ciphertext):
        calls.append((user_id, len(ciphertext)))
        return "luma-face-embeddings", f"embeddings/{user_id}/fake.bin"

    monkeypatch.setattr(face_store, "put_embedding", fake_put)
    monkeypatch.setattr(face_store, "delete_embedding", lambda *a, **k: None)
    return calls


@pytest.fixture
def client():
    return APIClient()


def _payload(**overrides):
    data = {
        "dni": "70111222",
        "identity_confirmed": True,
        "birth_date": (date.today() - timedelta(days=365 * 25)).isoformat(),
        "email": "nuevo.cliente@example.com",
        "password": "Clave-Segura-2026",
        "liveness": {"passed": True, "checks": ["blink", "turn_left"]},
        "face_descriptor": VALID_DESCRIPTOR,
        "descriptor_algorithm": "face-api ssdMobilenetv1 128d",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
class TestValidarDni:
    def test_ok_mock(self, client, settings):
        settings.DNI_VALIDATION_MODE = "mock"
        resp = client.post(reverse("accounts:validar-dni"), {"dni": "  70111222 "}, format="json")
        assert resp.status_code == 200
        body = resp.json()
        assert body["dni"] == "70111222"
        assert body["nombre_completo"]

    def test_bad_dni(self, client):
        resp = client.post(reverse("accounts:validar-dni"), {"dni": "123"}, format="json")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestRegistro:
    def test_happy_path_creates_customer(self, client, settings, _fake_minio):
        settings.DNI_VALIDATION_MODE = "mock"
        resp = client.post(reverse("accounts:registro"), _payload(), format="json")
        assert resp.status_code == 201, resp.content
        body = resp.json()

        assert body["account_number"] and len(body["account_number"]) == 20
        assert body["totp"]["secret"]
        assert body["totp"]["otpauth_uri"].startswith("otpauth://totp/")

        user = User.objects.get(email="nuevo.cliente@example.com")
        assert user.dni == "70111222"
        assert user.is_identity_verified is True
        assert user.check_password("Clave-Segura-2026")
        assert user.has_totp
        assert user.totp_secret_encrypted != ""

        emb = FaceEmbedding.objects.get(user=user)
        assert emb.dimensions == 128
        assert Account.objects.filter(user=user, number=body["account_number"]).exists()
        assert len(_fake_minio) == 1

    def test_rejects_under_18(self, client, settings):
        settings.DNI_VALIDATION_MODE = "mock"
        young = (date.today() - timedelta(days=365 * 17)).isoformat()
        resp = client.post(reverse("accounts:registro"), _payload(birth_date=young), format="json")
        assert resp.status_code == 400
        assert "18" in str(resp.json())

    def test_rejects_identity_not_confirmed(self, client, settings):
        settings.DNI_VALIDATION_MODE = "mock"
        resp = client.post(
            reverse("accounts:registro"), _payload(identity_confirmed=False), format="json"
        )
        assert resp.status_code == 400

    def test_rejects_failed_liveness(self, client, settings):
        settings.DNI_VALIDATION_MODE = "mock"
        resp = client.post(
            reverse("accounts:registro"),
            _payload(liveness={"passed": False, "checks": []}),
            format="json",
        )
        assert resp.status_code == 400

    def test_rejects_weak_password(self, client, settings):
        settings.DNI_VALIDATION_MODE = "mock"
        resp = client.post(
            reverse("accounts:registro"), _payload(password="12345678"), format="json"
        )
        assert resp.status_code == 400

    def test_rejects_duplicate_email(self, client, settings, _fake_minio):
        settings.DNI_VALIDATION_MODE = "mock"
        first = client.post(reverse("accounts:registro"), _payload(), format="json")
        assert first.status_code == 201
        resp = client.post(reverse("accounts:registro"), _payload(dni="70999888"), format="json")
        assert resp.status_code == 400
        assert "correo" in str(resp.json()).lower()

    def test_rejects_duplicate_dni(self, client, settings, _fake_minio):
        settings.DNI_VALIDATION_MODE = "mock"
        first = client.post(reverse("accounts:registro"), _payload(), format="json")
        assert first.status_code == 201
        resp = client.post(
            reverse("accounts:registro"),
            _payload(email="otro@example.com"),
            format="json",
        )
        assert resp.status_code == 400
        assert "dni" in str(resp.json()).lower()

    def test_rejects_short_descriptor(self, client, settings):
        settings.DNI_VALIDATION_MODE = "mock"
        resp = client.post(
            reverse("accounts:registro"), _payload(face_descriptor=[0.1, 0.2, 0.3]), format="json"
        )
        assert resp.status_code == 400
