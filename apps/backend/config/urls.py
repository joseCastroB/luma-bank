"""URL raiz de Luma Bank."""

from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from config.health import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    # Endpoints por dominio (se iran completando en cada sprint).
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/banking/", include("apps.banking.urls")),
    path("api/v1/cards/", include("apps.cards.urls")),
    # Metodo alterno de login (HU03): usuario/contrasena -> JWT. TOTP se
    # validara en la vista propia de accounts durante el Sprint 1.
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
