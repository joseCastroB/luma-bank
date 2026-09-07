"""HU02 - cifrado AES-256-GCM de embeddings y secreto TOTP."""

from apps.accounts.services import crypto


def test_embedding_roundtrip():
    vector = [0.1, -0.25, 3.14159, 0.0, -1.0] * 26  # 130 valores
    blob = crypto.encrypt_embedding(vector)
    assert isinstance(blob, bytes)
    assert blob != bytes(len(blob))  # no está en claro

    recovered = crypto.decrypt_embedding(blob)
    assert len(recovered) == len(vector)
    for a, b in zip(vector, recovered, strict=True):
        assert abs(a - b) < 1e-5


def test_secret_roundtrip():
    token = crypto.encrypt_secret("JBSWY3DPEHPK3PXP")
    assert token != "JBSWY3DPEHPK3PXP"
    assert crypto.decrypt_secret(token) == "JBSWY3DPEHPK3PXP"


def test_nonce_is_random():
    a = crypto.encrypt_bytes(b"same input")
    b = crypto.encrypt_bytes(b"same input")
    assert a != b
    assert crypto.decrypt_bytes(a) == crypto.decrypt_bytes(b) == b"same input"
