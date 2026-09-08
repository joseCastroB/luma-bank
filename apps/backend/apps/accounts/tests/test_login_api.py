"""HU03 - login facial + método alterno (contraseña + TOTP) + bloqueos."""

from datetime import date

import pyotp
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import LoginAttempt
from apps.accounts.services import face_store, registration

MATCH = [round(0.01 * i - 0.5, 4) for i in range(128)]
FAR = [x + 1.0 for x in MATCH]


@pytest.fixture
def face_backend(monkeypatch):
    """MinIO simulado en memoria: put_embedding guarda, get_embedding lee."""
    store: dict[tuple[str, str], bytes] = {}

    def put(user_id, ciphertext):
        key = f"embeddings/{user_id}/x.bin"
        store[("luma-face-embeddings", key)] = ciphertext
        return "luma-face-embeddings", key

    monkeypatch.setattr(face_store, "put_embedding", put)
    monkeypatch.setattr(face_store, "get_embedding", lambda b, k: store[(b, k)])
    monkeypatch.setattr(face_store, "delete_embedding", lambda *a, **k: None)
    return store


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def customer(db, face_backend, settings):
    settings.DNI_VALIDATION_MODE = "mock"
    return registration.register_customer(
        dni="70000001",
        birth_date=date(2000, 1, 1),
        email="cliente@example.com",
        password="Clave-Segura-2026",
        face_descriptor=MATCH,
        descriptor_algorithm="test",
    )


def _facial(client, descriptor, *, passed=True, identifier="cliente@example.com"):
    return client.post(
        reverse("accounts:login-facial"),
        {"identifier": identifier, "face_descriptor": descriptor, "liveness": {"passed": passed}},
        format="json",
    )


@pytest.mark.django_db
class TestFacialLogin:
    def test_success_returns_jwt(self, client, customer):
        resp = _facial(client, MATCH)
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["access"] and body["refresh"]
        assert body["user"]["email"] == "cliente@example.com"

    def test_unknown_user_is_generic(self, client, db):
        resp = _facial(client, MATCH, identifier="nadie@example.com")
        assert resp.status_code == 401
        assert "verificar" in resp.json()["detail"].lower()

    def test_no_match_first_time(self, client, customer):
        resp = _facial(client, FAR)
        assert resp.status_code == 401
        assert "fallback" not in resp.json()

    def test_two_failures_offer_fallback(self, client, customer):
        _facial(client, FAR)
        resp = _facial(client, FAR)
        assert resp.status_code == 401
        assert resp.json()["fallback"] == "password_totp"

    def test_failed_liveness_is_logged_suspicious(self, client, customer):
        resp = _facial(client, MATCH, passed=False)
        assert resp.status_code == 400
        attempt = LoginAttempt.objects.get(outcome=LoginAttempt.Outcome.BAD_LIVENESS)
        assert attempt.suspicious is True

    def test_five_failures_lock_account(self, client, customer):
        for _ in range(4):
            assert _facial(client, FAR).status_code == 401
        fifth = _facial(client, FAR)
        assert fifth.status_code == 423
        assert fifth.json()["locked_until"]
        # incluso con el rostro correcto, sigue bloqueada
        assert _facial(client, MATCH).status_code == 423


@pytest.mark.django_db
class TestPasswordTotpLogin:
    def _login(self, client, customer, *, password="Clave-Segura-2026", totp=None):
        code = totp if totp is not None else pyotp.TOTP(customer.totp_secret).now()
        return client.post(
            reverse("accounts:login-password"),
            {"identifier": "cliente@example.com", "password": password, "totp": code},
            format="json",
        )

    def test_success(self, client, customer):
        resp = self._login(client, customer)
        assert resp.status_code == 200
        assert resp.json()["access"]

    def test_bad_password(self, client, customer):
        assert self._login(client, customer, password="incorrecta12345").status_code == 401

    def test_bad_totp(self, client, customer):
        assert self._login(client, customer, totp="000000").status_code == 401

    def test_success_after_two_facial_fails(self, client, customer):
        _facial(client, FAR)
        _facial(client, FAR)
        assert self._login(client, customer).status_code == 200


@pytest.mark.django_db
class TestMe:
    def test_requires_auth(self, client):
        assert client.get(reverse("accounts:me")).status_code == 401

    def test_returns_profile_and_accounts(self, client, customer):
        token = _facial(client, MATCH).json()["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = client.get(reverse("accounts:me"))
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "cliente@example.com"
        assert len(body["accounts"]) == 1
        assert body["accounts"][0]["number"] == customer.account_number
