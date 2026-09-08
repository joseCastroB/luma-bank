from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import DniValidationLog, FaceEmbedding, User


@admin.register(User)
class LumaUserAdmin(UserAdmin):
    list_display = ("email", "dni", "full_name", "is_identity_verified", "is_active")
    search_fields = ("email", "dni", "first_name", "last_name")
    list_filter = ("is_identity_verified", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        (
            "Luma Bank",
            {"fields": ("dni", "birth_date", "is_identity_verified", "totp_secret_encrypted")},
        ),
    )
    readonly_fields = ("totp_secret_encrypted",)


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
