"""Rutas del dominio de cuentas."""

from django.urls import path

from .views import RegistroView, ValidarDniView
from .views_auth import FacialLoginView, MeView, PasswordLoginView

app_name = "accounts"

urlpatterns = [
    # HU02 - registro / apertura de cuenta
    path("registro/validar-dni/", ValidarDniView.as_view(), name="validar-dni"),
    path("registro/", RegistroView.as_view(), name="registro"),
    # HU03 - login
    path("login/facial/", FacialLoginView.as_view(), name="login-facial"),
    path("login/password/", PasswordLoginView.as_view(), name="login-password"),
    path("me/", MeView.as_view(), name="me"),
]
