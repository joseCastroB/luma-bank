from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "currency", "status", "balance", "opened_at")
    list_filter = ("status", "currency")
    search_fields = ("number", "user__email", "user__dni")
    readonly_fields = ("opened_at",)
