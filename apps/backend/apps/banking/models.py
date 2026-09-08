"""Modelos de operaciones bancarias. Sprint 1: Account (se crea al registrarse)."""

from __future__ import annotations

from django.db import models


class Account(models.Model):
    """Cuenta bancaria de un cliente."""

    class Status(models.TextChoices):
        ACTIVE = "active", "activa"
        FROZEN = "frozen", "congelada"
        CLOSED = "closed", "cerrada"

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    number = models.CharField("número de cuenta", max_length=20, unique=True)
    currency = models.CharField(max_length=3, default="PEN")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    opened_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "banking_account"
        verbose_name = "cuenta"
        verbose_name_plural = "cuentas"

    def __str__(self) -> str:
        return f"{self.number} ({self.user_id})"
