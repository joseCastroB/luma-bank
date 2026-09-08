"""Rutas del dominio de cuentas."""

from django.urls import path

from .views import RegistroView, ValidarDniView

app_name = "accounts"

urlpatterns = [
    # HU02 - registro / apertura de cuenta
    path("registro/validar-dni/", ValidarDniView.as_view(), name="validar-dni"),
    path("registro/", RegistroView.as_view(), name="registro"),
    # HU03 - login facial: se agrega en feature/HU03-login
]
