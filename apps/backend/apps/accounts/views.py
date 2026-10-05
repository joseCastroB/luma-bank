"""Vistas del dominio de cuentas (HU02: registro / apertura)."""

from __future__ import annotations

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import DniValidationLog
from .serializers import DniValidationSerializer, RegistroSerializer
from .services import liveness, registration
from .services.identity import (
    IdentityNotFound,
    IdentityServiceError,
    InvalidDni,
    LionApiQuotaExceeded,
    validate_dni,
)

logger = logging.getLogger("luma.accounts")


class LivenessChallengeView(APIView):
    """
    Paso 0 de todo lo que usa camara: emite el reto de prueba de vida.

    El cliente lo pide antes de capturar (registro y login facial). El reto es
    de un solo uso, vive en Valkey y caduca: si el usuario se equivoca tiene
    que pedir uno nuevo, no puede reintentar con el mismo.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "liveness_challenge"

    def post(self, request):
        challenge = liveness.issue_challenge()
        return Response(
            {
                "challenge_id": challenge.challenge_id,
                "plan": challenge.plan,
                "expires_in": challenge.expires_in,
            }
        )


class ValidarDniView(APIView):
    """Paso 1 del registro: valida el DNI contra RENIEC (o mock) y devuelve el nombre."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "dni_validation"

    def post(self, request):
        serializer = DniValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dni = serializer.validated_data["dni"]

        mode = settings.DNI_VALIDATION_MODE
        try:
            data = validate_dni(dni)
        except InvalidDni as exc:
            DniValidationLog.objects.create(
                dni=dni, mode=mode, result=DniValidationLog.Result.INVALID
            )
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except IdentityNotFound as exc:
            DniValidationLog.objects.create(
                dni=dni, mode=mode, result=DniValidationLog.Result.NOT_FOUND
            )
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except LionApiQuotaExceeded:
            # RNF-06: sin creditos no se bloquea al usuario. Este endpoint solo
            # informa datos, asi que se responde 202 para que el wizard de registro siga
            # y marque la identidad como pendiente, en vez de cortar el registro.
            logger.warning("LionAPI sin créditos al validar DNI %s", dni)
            DniValidationLog.objects.create(
                dni=dni, mode=mode, result=DniValidationLog.Result.ERROR
            )
            return Response(
                {
                    "detail": (
                        "No pudimos validar tu DNI por límite de consultas del "
                        "servicio. Podrás completar el registro, pero tu identidad "
                        "quedará pendiente de verificación."
                    ),
                    "identity_pending_review": True,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except IdentityServiceError as exc:
            logger.warning("Fallo LionAPI para DNI %s: %s", dni, exc)
            DniValidationLog.objects.create(
                dni=dni, mode=mode, result=DniValidationLog.Result.ERROR
            )
            return Response(
                {
                    "detail": (
                        "El servicio de validación de identidad no está disponible. "
                        "Intenta en unos minutos."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        DniValidationLog.objects.create(
            dni=dni,
            mode=mode,
            result=(
                DniValidationLog.Result.CACHED
                if data.source == "cache"
                else DniValidationLog.Result.FOUND
            ),
        )
        return Response(
            {
                "dni": data.dni,
                "nombres": data.nombres,
                "apellidos": data.apellidos,
                "nombre_completo": data.nombre_completo,
            }
        )


class RegistroView(APIView):
    """Paso 2 del registro: confirma identidad, prueba de vida y abre la cuenta."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "registro"

    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data

        # La prueba de vida se valida ANTES de tocar la base: si el reto es
        # invalido, vencido o esta mal ejecutado no se crea nada.
        try:
            attestation = liveness.consume_challenge(
                v["liveness"]["challenge_id"],
                v["liveness"]["completed_actions"],
            )
        except liveness.LivenessError as exc:
            return Response(
                {"detail": exc.message, "code": exc.code},
                status=exc.status,
            )

        # RNF-06 (degradacion con gracia): se intenta validar contra RENIEC.
        # Si la API solo esta sin creditos, el registro NO se bloquea: se crea
        # la cuenta degradada. Si la API esta CAIDA (error real), si se bloquea,
        # porque degradar por una falla tecnica abriria cuentas a ciegas.
        degraded = False
        try:
            result = registration.register_customer(
                dni=v["dni"],
                birth_date=v["birth_date"],
                email=v["email"],
                password=v["password"],
                face_descriptor=v["face_descriptor"],
                descriptor_algorithm=v["descriptor_algorithm"],
                attestation=attestation,
            )
        except LionApiQuotaExceeded:
            degraded = True
            logger.warning(
                "LionAPI sin créditos (RNF-06): registrando en modo degradado dni=%s", v["dni"]
            )
            if not v.get("full_name"):
                return Response(
                    {
                        "detail": (
                            "No pudimos validar tu DNI por límite de consultas del "
                            "servicio. Vuelve a intentarlo en unos minutos."
                        ),
                        "code": "identity_service_quota",
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            result = registration.register_customer(
                dni=v["dni"],
                birth_date=v["birth_date"],
                email=v["email"],
                password=v["password"],
                face_descriptor=v["face_descriptor"],
                descriptor_algorithm=v["descriptor_algorithm"],
                attestation=attestation,
                degraded=True,
                declared_full_name=v["full_name"],
            )
        except (IdentityNotFound, InvalidDni) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except IdentityServiceError:
            return Response(
                {
                    "detail": (
                        "El servicio de validación de identidad no está disponible. "
                        "Intenta en unos minutos."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except registration.DescriptorReplayError as exc:
            return Response(
                {"detail": str(exc), "code": "descriptor_replay"},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "account_number": result.account_number,
                "email": result.user.email,
                "full_name": result.full_name,
                "totp": {
                    "secret": result.totp_secret,
                    "otpauth_uri": result.totp_uri,
                    "issuer": "Luma Bank",
                },
                "message": "Cuenta creada. Guarda el código TOTP para el método de acceso alterno.",
                "identity_pending_review": degraded,
            },
            status=status.HTTP_201_CREATED,
        )
