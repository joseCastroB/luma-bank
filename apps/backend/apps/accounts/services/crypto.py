"""
Cifrado simétrico AES-256-GCM para datos en reposo:
- embeddings faciales antes de subirlos a MinIO
- secreto TOTP antes de guardarlo en PostgreSQL

La clave sale de settings.FACE_EMBEDDING_ENCRYPTION_KEY y DEBE medir
exactamente 32 bytes, en cualquiera de estas dos formas:
- base64-urlsafe de 32 bytes (44 chars, terminado en '=')
- hex de 32 bytes (64 chars)

No hay fallback: una clave de otra longitud es un error de configuracion y
aborta el arranque. Derivar la clave con SHA-256 sobre un string arbitrario
parece tolerante pero permite desplegar con una clave debil o mal escrita
sin que nadie lo note, que es justo lo que RNF-13 seeks evitar.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
from array import array

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

_NONCE_BYTES = 12
_KEY_BYTES = 32
_FINGERPRINT_INFO = b"luma-fingerprint-v1"


def _load_key() -> bytes:
    raw = getattr(settings, "FACE_EMBEDDING_ENCRYPTION_KEY", "") or ""
    if not raw:
        raise ImproperlyConfigured(
            "FACE_EMBEDDING_ENCRYPTION_KEY no está definida: no se puede cifrar "
            "el embedding facial ni el secreto TOTP."
        )
    # base64-urlsafe de 32 bytes
    try:
        decoded = base64.urlsafe_b64decode(raw)
        if len(decoded) == _KEY_BYTES:
            return decoded
    except (ValueError, binascii.Error):
        pass
    # hex de 32 bytes
    try:
        decoded = bytes.fromhex(raw)
        if len(decoded) == _KEY_BYTES:
            return decoded
    except ValueError:
        pass
    raise ImproperlyConfigured(
        f"FACE_EMBEDDING_ENCRYPTION_KEY debe tener {_KEY_BYTES} bytes exactos "
        f"en base64-urlsafe (44 chars) o hex (64 chars); la clave informada "
        f"decodifica a {len(raw)} chars y no es una clave válida de AES-256. "
        'Generá una con: python -c "import base64,os;'
        'print(base64.urlsafe_b64encode(os.urandom(32)).decode())"'
    )


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


# --- Huella del descriptor (anti-replay) --------------------------------


def _fingerprint_key() -> bytes:
    """Subclave derivada de la clave maestra: separa usos de la misma clave."""
    return hmac.new(_load_key(), _FINGERPRINT_INFO, hashlib.sha256).digest()


def descriptor_fingerprint(vector: list[float]) -> str:
    """
    HMAC-SHA256 del descriptor, en hex.

    Permite localizar en O(1) dos registros que comparten exactamente el mismo
    vector (alguien que reusa la captura de otro) apoyandose en el indice
    unico de accounts_face_embedding.descriptor_fingerprint, sin descifrar ni
    comparar todos los embeddings guardados en MinIO.

    No es reversible hacia el vector: sin la clave del servidor, el HMAC no
    permite recuperar el embedding. Solo detecta igualdad exacta.
    """
    packed = array("f", vector).tobytes()
    return hmac.new(_fingerprint_key(), packed, hashlib.sha256).hexdigest()


# --- Secreto TOTP (string corto) ---------------------------------------


def encrypt_secret(secret: str) -> str:
    return base64.b64encode(encrypt_bytes(secret.encode())).decode()


def decrypt_secret(token: str) -> str:
    return decrypt_bytes(base64.b64decode(token)).decode()
