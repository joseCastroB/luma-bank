"""Vistas de inicio de sesión (HU03: facial + método alterno contraseña/TOTP)."""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import LoginAttempt
from .serializers import FacialLoginSerializer, PasswordLoginSerializer
from .services import auth

logger = logging.getLogger("luma.auth")

GENERIC_FAIL = "No pudimos verificar tu identidad. Revisa los datos e intenta de nuevo."


def _meta(request) -> dict:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")
    return {"ip_address": ip or None, "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300]}


def _log(identifier, method, outcome, *, user=None, suspicious=False, meta=None):
    LoginAttempt.objects.create(
        user=user,
        identifier=identifier[:254],
        method=method,
        outcome=outcome,
        suspicious=suspicious,
        **(meta or {}),
    )


def _tokens(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def _user_public(user) -> dict:
    return {"email": user.email, "full_name": user.full_name, "dni": user.dni}


def _locked_response(user, identifier, method, meta):
    _log(identifier, method, LoginAttempt.Outcome.LOCKED, user=user, suspicious=True, meta=meta)
    return Response(
        {
            "detail": (
                "Cuenta bloqueada temporalmente por múltiples intentos fallidos. "
                "Inténtalo más tarde."
            ),
            "locked_until": user.locked_until,
        },
        status=status.HTTP_423_LOCKED,
    )


class FacialLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = FacialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data
        identifier = v["identifier"].strip()
        meta = _meta(request)
        method = LoginAttempt.Method.FACIAL

        user = auth.resolve_user(identifier)
        if user is None:
            _log(identifier, method, LoginAttempt.Outcome.UNKNOWN_USER, meta=meta)
            return Response({"detail": GENERIC_FAIL}, status=status.HTTP_401_UNAUTHORIZED)

        if auth.is_locked(user):
            return _locked_response(user, identifier, method, meta)

        if not v["liveness"]["passed"]:
            locked = auth._register_failure(user, facial=True)
            _log(
                identifier,
                method,
                LoginAttempt.Outcome.BAD_LIVENESS,
                user=user,
                suspicious=True,
                meta=meta,
            )
            if locked:
                return _locked_response(user, identifier, method, meta)
            return Response(
                {"detail": "No se completó la prueba de vida. El intento quedó registrado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            check = auth.verify_face(user, v["face_descriptor"])
        except auth.LoginError as exc:
            return Response({"detail": exc.message}, status=exc.status)

        if check.matched:
            auth.reset_failures(user)
            _log(identifier, method, LoginAttempt.Outcome.SUCCESS, user=user, meta=meta)
            return Response({**_tokens(user), "user": _user_public(user)})

        locked = auth._register_failure(user, facial=True)
        _log(identifier, method, LoginAttempt.Outcome.BAD_FACE, user=user, meta=meta)
        if locked:
            return _locked_response(user, identifier, method, meta)

        body = {"detail": "No te reconocimos. Acomódate frente a la cámara e intenta de nuevo."}
        if auth.should_offer_fallback(user):
            body["fallback"] = "password_totp"
            body["detail"] = (
                "No pudimos reconocerte tras varios intentos. Usa tu correo, contraseña y código."
            )
        return Response(body, status=status.HTTP_401_UNAUTHORIZED)


class PasswordLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = PasswordLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data
        identifier = v["identifier"].strip()
        meta = _meta(request)
        method = LoginAttempt.Method.PASSWORD_TOTP

        user = auth.resolve_user(identifier)
        if user is None:
            _log(identifier, method, LoginAttempt.Outcome.UNKNOWN_USER, meta=meta)
            return Response({"detail": GENERIC_FAIL}, status=status.HTTP_401_UNAUTHORIZED)

        if auth.is_locked(user):
            return _locked_response(user, identifier, method, meta)

        if not user.check_password(v["password"]):
            locked = auth._register_failure(user, facial=False)
            _log(identifier, method, LoginAttempt.Outcome.BAD_PASSWORD, user=user, meta=meta)
            if locked:
                return _locked_response(user, identifier, method, meta)
            return Response({"detail": GENERIC_FAIL}, status=status.HTTP_401_UNAUTHORIZED)

        if not auth.verify_totp(user, v["totp"]):
            locked = auth._register_failure(user, facial=False)
            _log(identifier, method, LoginAttempt.Outcome.BAD_TOTP, user=user, meta=meta)
            if locked:
                return _locked_response(user, identifier, method, meta)
            return Response(
                {"detail": "Código de verificación incorrecto."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        auth.reset_failures(user)
        _log(identifier, method, LoginAttempt.Outcome.SUCCESS, user=user, meta=meta)
        return Response({**_tokens(user), "user": _user_public(user)})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        accounts = [
            {
                "number": a.number,
                "currency": a.currency,
                "status": a.status,
                "balance": str(a.balance),
                "opened_at": a.opened_at,
            }
            for a in user.accounts.all()
        ]
        return Response({**_user_public(user), "accounts": accounts})
