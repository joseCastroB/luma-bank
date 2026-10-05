"""Rutas del dominio de cuentas."""

from django.urls import path

from .views import LivenessChallengeView, RegistroView, ValidarDniView
from .views_auth import FacialLoginView, MeView, PasswordLoginView

app_name = "accounts"

urlpatterns = [
    # HU02 - registro / apertura de cuenta
    path("registro/validar-dni/", ValidarDniView.as_view(), name="validar-dni"),
    path("registro/", RegistroView.as_view(), name="registro"),
    # Prueba de vida: reto aleatorio de un solo uso (registro y login facial)
    path("liveness/challenge/", LivenessChallengeView.as_view(), name="liveness-challenge"),
    # HU03 - login
    path("login/facial/", FacialLoginView.as_view(), name="login-facial"),
    path("login/password/", PasswordLoginView.as_view(), name="login-password"),
    path("me/", MeView.as_view(), name="me"),
]
