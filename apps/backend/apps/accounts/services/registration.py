"""
Orquestación del registro / apertura de cuenta (HU02).

Pasos (todos ya validados por el serializer):
1. Revalidar identidad por DNI (server-side; normalmente cae en caché de Valkey).
2. Crear el usuario (username = email), con nombre de RENIEC y +18 verificado.
3. Generar secreto TOTP y guardarlo cifrado (segundo factor del método alterno).
4. Cifrar el embedding facial (AES-256-GCM) y subirlo a MinIO; guardar la ref.
5. Abrir la cuenta y devolver el número.

La prueba de vida NO se ejecuta acá: llega ya consumida y validada por la vista
contra el reto que emitió el servidor (services/liveness.py). Este servicio
solo la persiste como evidencia auditable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pyotp
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.banking.services import open_account

from ..models import FaceEmbedding, LivenessAttestation
from . import crypto, face_store
from .identity import validate_dni

logger = logging.getLogger("luma.registration")
User = get_user_model()


class DescriptorReplayError(Exception):
    """
    El descriptor ya fue registrado por otro cliente.

    Indica que alguien esta reusando una captura facial ajena: el mismo vector
    exacto ya esta en el sistema. Es la senal de intento de suplantacion.
    """


def _split_degraded_name(declared_full_name: str) -> tuple[str, str]:
    """
    Reparte el nombre declarado por el usuario entre first_name y last_name.

    Solo aplica en registro degradado, donde no hay nombre oficial de RENIEC.
    Django separa nombre y apellido en dos campos, asi que se toma el ultimo
    token como apellido y el resto como nombres. Es una convencion, NO un dato
    verificado: por eso la cuenta queda con is_identity_verified=False.
    """
    parts = [p for p in declared_full_name.strip().split() if p]
    if not parts:
        return ("PENDIENTE DE VERIFICAR", "")
    if len(parts) == 1:
        return (parts[0][:150], "")
    return (" ".join(parts[:-1])[:150], parts[-1][:150])


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
    attestation,
    degraded: bool = False,
    declared_full_name: str = "",
) -> RegistrationResult:
    """
    Crea el cliente y abre su cuenta.

    `degraded=True` implementa RNF-06: cuando RENIEC/LionAPI no permite validar
    el DNI (agotamiento de créditos), NO se bloquea el registro. La cuenta se
    abre igual pero el usuario queda con `is_identity_verified=False`, es decir
    sin nombre oficial ni confirmación de que sea mayor de 18 años.

    Consecuencias que hay que asumir al usar este modo:
      - El nombre del usuario es lo que el frontend envio, no el oficial.
      - El +18 NO se puede verificar contra RENIEC. Se trusts en lo que el
        cliente declara en birth_date, lo cual es solo una declaracion.
      - Por eso la cuenta queda BLOQUEADA para operar hasta que un analista
        confirme la identidad a mano.

    Es una concession consciente para no perder al cliente por una API de
    terceros caida. No se debe usar como atajo: la cuenta no es operativa.
    """
    if degraded:
        logger.warning(
            "Registro degradado (RNF-06) sin validar identidad contra RENIEC: dni=%s", dni
        )
        official_dni = dni
        first_name, last_name = _split_degraded_name(declared_full_name)
        identity_verified = False
    else:
        data = validate_dni(dni)
        official_dni = data.dni
        first_name, last_name = data.nombres, data.apellidos
        identity_verified = True

    fingerprint = crypto.descriptor_fingerprint(face_descriptor)
    if FaceEmbedding.objects.filter(descriptor_fingerprint=fingerprint).exists():
        logger.warning(
            "Intento de replay de descriptor: el vector ya pertenece a otra cuenta (dni=%s)",
            dni,
        )
        raise DescriptorReplayError(
            "Ese rostro ya está registrado en otra cuenta. "
            "Si no es tuyo, repórtalo desde la opción de soporte."
        )

    user = User(
        username=email,
        email=email,
        dni=official_dni,
        first_name=first_name[:150],
        last_name=last_name[:150],
        birth_date=birth_date,
        is_identity_verified=identity_verified,
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
            descriptor_fingerprint=fingerprint,
        )
        LivenessAttestation.objects.create(
            user=user,
            context=LivenessAttestation.Context.REGISTRO,
            challenge_id=attestation.challenge_id,
            plan=attestation.plan,
            completed_actions=attestation.completed_actions,
            duration_ms=attestation.duration_ms,
            descriptor_algorithm=descriptor_algorithm[:128],
        )
        account = open_account(user)
    except IntegrityError:
        # Carrera: dos registros con el mismo descriptor pasaron el EXISTS y
        # chocaron contra el indice unico de descriptor_fingerprint.
        face_store.delete_embedding(bucket, object_key)
        raise DescriptorReplayError("Ese rostro ya está registrado en otra cuenta.") from None
    except Exception:
        face_store.delete_embedding(bucket, object_key)
        raise

    totp_uri = pyotp.TOTP(totp_secret).provisioning_uri(
        name=email, issuer_name=settings.TOTP_ISSUER
    )
    logger.info(
        "Cliente registrado: user=%s cuenta=%s identidad_verificada=%s",
        user.pk,
        account.number,
        identity_verified,
    )
    return RegistrationResult(
        user=user,
        account_number=account.number,
        full_name=user.full_name,
        totp_secret=totp_secret,
        totp_uri=totp_uri,
    )
