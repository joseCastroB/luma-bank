"""
Orquestación del registro / apertura de cuenta (HU02).

Pasos (todos ya validados por el serializer):
1. Revalidar identidad por DNI (server-side; normalmente cae en caché de Valkey).
2. Crear el usuario (username = email), con nombre de RENIEC y +18 verificado.
3. Generar secreto TOTP y guardarlo cifrado (segundo factor del método alterno).
4. Cifrar el embedding facial (AES-256-GCM) y subirlo a MinIO; guardar la ref.
5. Abrir la cuenta y devolver el número.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pyotp
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.banking.services import open_account

from ..models import FaceEmbedding
from . import crypto, face_store
from .identity import DniData, validate_dni

logger = logging.getLogger("luma.registration")
User = get_user_model()


@dataclass
class RegistrationResult:
    user: object
    account_number: str
    full_name: str
    totp_secret: str
    totp_uri: str


@transaction.atomic
def register_customer(
    *,
    dni: str,
    birth_date,
    email: str,
    password: str,
    face_descriptor: list[float],
    descriptor_algorithm: str,
) -> RegistrationResult:
    identity: DniData = validate_dni(dni)

    user = User(
        username=email,
        email=email,
        dni=identity.dni,
        first_name=identity.nombres[:150],
        last_name=identity.apellidos[:150],
        birth_date=birth_date,
        is_identity_verified=True,
    )
    user.set_password(password)

    totp_secret = pyotp.random_base32()
    user.totp_secret_encrypted = crypto.encrypt_secret(totp_secret)
    user.save()

    # Cifrar + subir el embedding. Si algo falla, la transacción revierte al
    # usuario; borramos el objeto huérfano best-effort.
    ciphertext = crypto.encrypt_embedding(face_descriptor)
    bucket, object_key = face_store.put_embedding(user.pk, ciphertext)
    try:
        FaceEmbedding.objects.create(
            user=user,
            bucket=bucket,
            object_key=object_key,
            algorithm=descriptor_algorithm[:128],
            dimensions=len(face_descriptor),
        )
        account = open_account(user)
    except Exception:
        face_store.delete_embedding(bucket, object_key)
        raise

    totp_uri = pyotp.TOTP(totp_secret).provisioning_uri(
        name=email, issuer_name=settings.TOTP_ISSUER
    )
    logger.info("Cliente registrado: user=%s cuenta=%s", user.pk, account.number)
    return RegistrationResult(
        user=user,
        account_number=account.number,
        full_name=user.full_name,
        totp_secret=totp_secret,
        totp_uri=totp_uri,
    )
