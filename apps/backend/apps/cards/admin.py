from django.contrib import admin

from .models import Card, CardTransaction

admin.site.register(Card)
admin.site.register(CardTransaction)
