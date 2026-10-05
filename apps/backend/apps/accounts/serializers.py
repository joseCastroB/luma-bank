"""Serializers del dominio de cuentas (HU02: registro / apertura)."""

from __future__ import annotations

import math
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .services import liveness
from .services.identity import InvalidDni, normalize_dni

User = get_user_model()

MIN_DESCRIPTOR_LEN = 64
MAX_DESCRIPTOR_LEN = 1024


def _years_since(d: date) -> int:
    today = date.today()
    return today.year - d.year - ((today.month, today.day) < (d.month, d.day))


class DniField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            return normalize_dni(value)
        except InvalidDni as exc:
            raise serializers.ValidationError(str(exc)) from exc


class DniValidationSerializer(serializers.Serializer):
    dni = DniField()


class LivenessSerializer(serializers.Serializer):
    """
    Respuesta del cliente al reto de vida emitido por el servidor.

    El cliente ya no declara `passed`: eso era una asercion del navegador que
    cualquiera podia mandar por curl. Ahora declara QUE GESTOS ejecuto y el
    servidor decide si la secuencia es la que sorteo (services/liveness.py).
    """

    challenge_id = serializers.CharField(max_length=64)
    completed_actions = serializers.ListField(
        child=serializers.ChoiceField(choices=liveness.ACTIONS),
        allow_empty=False,
        help_text="Gestos ejecutados, en el orden en que se completaron.",
    )

    def validate_completed_actions(self, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise serializers.ValidationError(
                "Un gesto no puede completarse dos veces en el mismo reto."
            )
        return value


class RegistroSerializer(serializers.Serializer):
    dni = DniField()
    identity_confirmed = serializers.BooleanField()
    birth_date = serializers.DateField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    liveness = LivenessSerializer()
    face_descriptor = serializers.ListField(child=serializers.FloatField())
    descriptor_algorithm = serializers.CharField(
        required=False,
        default="face-api ssdMobilenetv1 128d",
        max_length=128,
    )
    # Solo se usa en registro degradado (RNF-06), cuando RENIEC no devolvio el
    # nombre oficial. Opcional en el payload normal porque ahí manda LionAPI.
    full_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=300,
    )

    def validate_full_name(self, value: str) -> str:
        if value and not value.strip():
            raise serializers.ValidationError("El nombre no puede quedar vacío.")
        return value.strip()

    def validate_identity_confirmed(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "Debes confirmar que los datos de identidad son correctos."
            )
        return value

    def validate_email(self, value: str) -> str:
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo.")
        return value

    def validate_birth_date(self, value: date) -> date:
        if value > date.today():
            raise serializers.ValidationError("La fecha de nacimiento no puede ser futura.")
        if _years_since(value) < settings.MIN_SIGNUP_AGE_YEARS:
            raise serializers.ValidationError(
                f"Debes ser mayor de {settings.MIN_SIGNUP_AGE_YEARS} años para abrir una cuenta."
            )
        return value

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate_face_descriptor(self, value: list[float]) -> list[float]:
        if not (MIN_DESCRIPTOR_LEN <= len(value) <= MAX_DESCRIPTOR_LEN):
            raise serializers.ValidationError(
                f"El descriptor facial debe tener entre {MIN_DESCRIPTOR_LEN} y "
                f"{MAX_DESCRIPTOR_LEN} valores."
            )
        if any(not math.isfinite(x) for x in value):
            raise serializers.ValidationError("El descriptor facial contiene valores inválidos.")
        return value

    def validate(self, attrs: dict) -> dict:
        if User.objects.filter(dni=attrs["dni"]).exists():
            raise serializers.ValidationError({"dni": "Este DNI ya está registrado."})
        return attrs


class _DescriptorField(serializers.ListField):
    child = serializers.FloatField()

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not (MIN_DESCRIPTOR_LEN <= len(value) <= MAX_DESCRIPTOR_LEN):
            raise serializers.ValidationError(
                f"El descriptor facial debe tener entre {MIN_DESCRIPTOR_LEN} y "
                f"{MAX_DESCRIPTOR_LEN} valores."
            )
        if any(not math.isfinite(x) for x in value):
            raise serializers.ValidationError("El descriptor facial contiene valores inválidos.")
        return value


class FacialLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    face_descriptor = _DescriptorField()
    liveness = LivenessSerializer()


class PasswordLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    totp = serializers.CharField()
