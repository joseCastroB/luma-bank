"""
Cifrado simétrico AES-256-GCM para datos en reposo:
- embeddings faciales antes de subirlos a MinIO
- secreto TOTP antes de guardarlo en PostgreSQL

La clave sale de settings.FACE_EMBEDDING_ENCRYPTION_KEY. Acepta:
- base64-urlsafe de 32 bytes (44 chars)
- hex de 32 bytes (64 chars)
- cualquier otra cadena -> se deriva con SHA-256 (fallback)
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import os
from array import array

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

logger = logging.getLogger("luma.crypto")

_NONCE_BYTES = 12


def _load_key() -> bytes:
    raw = getattr(settings, "FACE_EMBEDDING_ENCRYPTION_KEY", "") or ""
    if not raw:
        # Sin clave explícita: se deriva del SECRET_KEY para no bloquear el
        # desarrollo. config.settings.prod EXIGE la variable y aborta el arranque
        # si falta, así que este camino solo ocurre en dev/tests.
        logger.warning(
            "FACE_EMBEDDING_ENCRYPTION_KEY no está definida; usando una clave "
            "derivada del SECRET_KEY (solo desarrollo). Define la variable en .env."
        )
        return hashlib.sha256(f"luma-dev-embedding-key:{settings.SECRET_KEY}".encode()).digest()
    # base64-urlsafe de 32 bytes
    try:
        decoded = base64.urlsafe_b64decode(raw)
        if len(decoded) == 32:
            return decoded
    except (ValueError, binascii.Error):
        pass
    # hex de 32 bytes
    try:
        decoded = bytes.fromhex(raw)
        if len(decoded) == 32:
            return decoded
    except ValueError:
        pass
    # fallback determinista
    return hashlib.sha256(raw.encode()).digest()


def encrypt_bytes(plaintext: bytes) -> bytes:
    """Devuelve nonce(12) || ciphertext||tag."""
    key = _load_key()
    nonce = os.urandom(_NONCE_BYTES)
    ct = AESGCM(key).encrypt(nonce, plaintext, None)
    return nonce + ct


def decrypt_bytes(blob: bytes) -> bytes:
    key = _load_key()
    nonce, ct = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
    return AESGCM(key).decrypt(nonce, ct, None)


# --- Embeddings faciales (lista de floats) -------------------------------


def encrypt_embedding(vector: list[float]) -> bytes:
    packed = array("f", vector).tobytes()
    return encrypt_bytes(packed)


def decrypt_embedding(blob: bytes) -> list[float]:
    packed = decrypt_bytes(blob)
    arr = array("f")
    arr.frombytes(packed)
    return list(arr)


# --- Secreto TOTP (string corto) ---------------------------------------


def encrypt_secret(secret: str) -> str:
    return base64.b64encode(encrypt_bytes(secret.encode())).decode()


def decrypt_secret(token: str) -> str:
    return decrypt_bytes(base64.b64decode(token)).decode()
