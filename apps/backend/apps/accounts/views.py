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
from .services import registration
from .services.identity import (
    IdentityNotFound,
    IdentityServiceError,
    InvalidDni,
    validate_dni,
)

logger = logging.getLogger("luma.accounts")


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
        except IdentityServiceError as exc:
            logger.warning("Fallo LionAPI para DNI %s: %s", dni, exc)
            DniValidationLog.objects.create(
                dni=dni, mode=mode, result=DniValidationLog.Result.ERROR
            )
            return Response(
                {"detail": "El servicio de validación de identidad no está disponible."},
                status=status.HTTP_502_BAD_GATEWAY,
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

        try:
            result = registration.register_customer(
                dni=v["dni"],
                birth_date=v["birth_date"],
                email=v["email"],
                password=v["password"],
                face_descriptor=v["face_descriptor"],
                descriptor_algorithm=v["descriptor_algorithm"],
            )
        except (IdentityNotFound, InvalidDni) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except IdentityServiceError:
            return Response(
                {"detail": "El servicio de validación de identidad no está disponible."},
                status=status.HTTP_502_BAD_GATEWAY,
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
            },
            status=status.HTTP_201_CREATED,
        )
