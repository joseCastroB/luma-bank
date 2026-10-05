"""HU03 - login facial + método alterno (contraseña + TOTP) + bloqueos."""

from datetime import date, timedelta

import pyotp
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import LivenessAttestation, LoginAttempt
from apps.accounts.services import face_store, registration

MATCH = [round(0.01 * i - 0.5, 4) for i in range(128)]
FAR = [x + 1.0 for x in MATCH]


def settings_count(n: int) -> int:
    """Evita el shadowing de `settings` (el fixture de pytest) en los helpers."""
    return n


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
def customer(db, face_backend, settings, make_attestation):
    settings.DNI_VALIDATION_MODE = "mock"
    return registration.register_customer(
        dni="70000001",
        birth_date=date(2000, 1, 1),
        email="cliente@example.com",
        password="Clave-Segura-2026",
        face_descriptor=MATCH,
        descriptor_algorithm="test",
        attestation=make_attestation(),
    )


def _facial(client, descriptor, *, proof=None, challenge=None, identifier="cliente@example.com"):
    """Login facial. `proof` permite inyectar una vivacidad manipulada."""
    return client.post(
        reverse("accounts:login-facial"),
        {
            "identifier": identifier,
            "face_descriptor": descriptor,
            "liveness": challenge() if proof is None else proof,
        },
        format="json",
    )


@pytest.mark.django_db
class TestFacialLogin:
    def test_success_returns_jwt(self, client, customer, fast_challenge):
        resp = _facial(client, MATCH, challenge=fast_challenge)
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["access"] and body["refresh"]
        assert body["user"]["email"] == "cliente@example.com"

    def test_success_persists_liveness_attestation(self, client, customer, fast_challenge):
        proof = fast_challenge()
        resp = _facial(client, MATCH, proof=proof)
        assert resp.status_code == 200, resp.content

        att = LivenessAttestation.objects.get(
            user=customer.user, context=LivenessAttestation.Context.LOGIN
        )
        assert att.challenge_id == proof["challenge_id"]

    def test_unknown_user_is_generic(self, client, db, fast_challenge):
        resp = _facial(client, MATCH, identifier="nadie@example.com", challenge=fast_challenge)
        assert resp.status_code == 401
        assert "verificar" in resp.json()["detail"].lower()

    def test_no_match_first_time(self, client, customer, fast_challenge):
        resp = _facial(client, FAR, challenge=fast_challenge)
        assert resp.status_code == 401
        assert "fallback" not in resp.json()

    def test_two_failures_offer_fallback(self, client, customer, fast_challenge):
        _facial(client, FAR, challenge=fast_challenge)
        resp = _facial(client, FAR, challenge=fast_challenge)
        assert resp.status_code == 401
        assert resp.json()["fallback"] == "password_totp"

    def test_tampered_liveness_is_logged_suspicious(self, client, customer, issue_live_challenge):
        """
        El cliente afirma los gestos pero en otro orden: es un intento forgery.

        Se registra como sospechoso, pero NO cuenta como fallo facial porque el
        scorer facial legitimo nunca llego a evaluarse.
        """
        proof = issue_live_challenge(completed_actions=["blink"])
        resp = _facial(client, MATCH, proof=proof)
        assert resp.status_code == 400
        attempt = LoginAttempt.objects.get(outcome=LoginAttempt.Outcome.BAD_LIVENESS)
        assert attempt.suspicious is True
        customer.user.refresh_from_db()
        assert customer.user.failed_facial_attempts == 0

    def test_liveness_challenge_cannot_be_replayed(self, client, customer, fast_challenge):
        """El mismo reto no sirve para dos intentos, ni siquiera con el rostro correcto."""
        proof = fast_challenge()
        assert _facial(client, MATCH, proof=proof).status_code == 200
        replay = _facial(client, MATCH, proof=proof)
        assert replay.status_code == 400
        assert replay.json().get("code") in {"challenge_expired", "challenge_consumed"}

    def test_five_failures_lock_account(self, client, customer, fast_challenge):
        for _ in range(4):
            assert _facial(client, FAR, challenge=fast_challenge).status_code == 401
        fifth = _facial(client, FAR, challenge=fast_challenge)
        assert fifth.status_code == 423
        assert fifth.json()["locked_until"]
        # incluso con el rostro correcto, sigue bloqueada
        assert _facial(client, MATCH, challenge=fast_challenge).status_code == 423


@pytest.mark.django_db
class TestLockout:
    def test_expired_lock_resets_counters(self, client, customer, fast_challenge):
        """
        Regresion del bug de bloqueo permanente.

        Antes, `failed_login_attempts` solo se ponia en cero al iniciar sesion
        con EXITO. Un cliente que llegaba al limite (5) y esperaba el vencimiento
        conservaba el 5: su primer fallo posterior lo re-bloqueaba al instante y
        la cuenta quedaba impracticable sin intervencion humana.
        """
        user = customer.user
        user.failed_login_attempts = settings_count(5)
        user.failed_facial_attempts = 5
        user.locked_until = timezone.now() - timedelta(minutes=1)  # vencido
        user.save()

        resp = _facial(client, FAR, challenge=fast_challenge)
        assert resp.status_code == 401, "no debe re-bloquear: el bloqueo ya vencio"
        assert "locked_until" not in resp.json()

        user.refresh_from_db()
        assert user.failed_login_attempts == 1, "el contador debe reiniciar, no seguir en 6"
        assert user.locked_until is None

    def test_active_lock_still_blocks(self, client, customer, fast_challenge):
        """Un bloqueo vigente sigue bloqueando, sin reiniciar contadores."""
        user = customer.user
        user.failed_login_attempts = 5
        user.locked_until = timezone.now() + timedelta(minutes=10)
        user.save()

        resp = _facial(client, MATCH, challenge=fast_challenge)
        assert resp.status_code == 423
        user.refresh_from_db()
        assert user.failed_login_attempts == 5


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

    def test_success_after_two_facial_fails(self, client, customer, fast_challenge):
        _facial(client, FAR, challenge=fast_challenge)
        _facial(client, FAR, challenge=fast_challenge)
        assert self._login(client, customer).status_code == 200


@pytest.mark.django_db
class TestMe:
    def test_requires_auth(self, client):
        assert client.get(reverse("accounts:me")).status_code == 401

    def test_returns_profile_and_accounts(self, client, customer, fast_challenge):
        token = _facial(client, MATCH, challenge=fast_challenge).json()["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = client.get(reverse("accounts:me"))
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "cliente@example.com"
        assert len(body["accounts"]) == 1
        assert body["accounts"][0]["number"] == customer.account_number
