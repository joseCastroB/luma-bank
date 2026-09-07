from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class LumaUserAdmin(UserAdmin):
    list_display = ("username", "dni", "email", "is_staff", "is_active")
    search_fields = ("username", "dni", "email")
    fieldsets = UserAdmin.fieldsets + (("Luma Bank", {"fields": ("dni",)}),)
