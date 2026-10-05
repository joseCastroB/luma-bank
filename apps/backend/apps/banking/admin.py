from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "currency", "status", "balance", "opened_at")
    list_filter = ("status", "currency")
    search_fields = ("number", "user__email", "user__dni")
    readonly_fields = ("opened_at",)


from .models import Beneficiary, Transaction, Transfer  # noqa: E402

admin.site.register(Beneficiary)
admin.site.register(Transfer)
admin.site.register(Transaction)
