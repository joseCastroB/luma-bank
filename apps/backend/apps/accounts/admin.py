from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from .models import AuditLog, DniValidationLog, FaceEmbedding, LoginAttempt, User
from .services import audit, auth


@admin.register(User)
class LumaUserAdmin(UserAdmin):
    list_display = (
        "email",
        "dni",
        "full_name",
        "is_identity_verified",
        "locked_until",
        "is_active",
    )
    search_fields = ("email", "dni", "first_name", "last_name")
    list_filter = ("is_identity_verified", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        (
            "Luma Bank",
            {
                "fields": (
                    "dni",
                    "birth_date",
                    "is_identity_verified",
                    "totp_secret_encrypted",
                    "failed_facial_attempts",
                    "failed_login_attempts",
                    "locked_until",
                )
            },
        ),
    )
    # El bloqueo solo se levanta con la acción, que deja registro de auditoría.
    readonly_fields = (
        "totp_secret_encrypted",
        "failed_facial_attempts",
        "failed_login_attempts",
        "locked_until",
    )
    actions = ["desbloquear_cuentas"]

    @admin.action(description="Desbloquear cuentas seleccionadas", permissions=["change"])
    def desbloquear_cuentas(self, request, queryset):
        unlocked = 0
        for user in queryset.filter(locked_until__gt=timezone.now()):
            auth.reset_failures(user)
            audit.record(request, "account.unlock", entity="usuario", entity_id=str(user.pk))
            unlocked += 1
        self.message_user(request, f"Cuentas desbloqueadas: {unlocked}.", messages.SUCCESS)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("identifier", "method", "outcome", "suspicious", "ip_address", "created_at")
    list_filter = ("method", "outcome", "suspicious")
    search_fields = ("identifier", "ip_address")
    readonly_fields = tuple(f.name for f in LoginAttempt._meta.fields)


@admin.register(FaceEmbedding)
class FaceEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("user", "bucket", "object_key", "dimensions", "algorithm", "created_at")
    search_fields = ("user__email", "object_key")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DniValidationLog)
class DniValidationLogAdmin(admin.ModelAdmin):
    list_display = ("dni", "mode", "result", "created_at")
    list_filter = ("mode", "result")
    search_fields = ("dni",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Solo lectura: la bitácora no se edita ni se borra."""

    list_display = ("created_at", "action", "user", "entity", "entity_id", "ip_address")
    list_filter = ("action", "entity")
    search_fields = ("action", "entity_id", "user__email")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
