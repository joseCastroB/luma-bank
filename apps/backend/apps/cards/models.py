"""Modelos de tarjetas (débito/crédito) y sus consumos."""

from __future__ import annotations

from django.db import models


class Card(models.Model):
    """
    Tarjeta de un cliente.

    Por seguridad (PCI DSS) NUNCA se guarda el número completo ni el CVV:
    solo los últimos 4 dígitos y un token opaco que identifica la tarjeta.
    """

    class Kind(models.TextChoices):
        DEBIT = "debit", "débito"
        CREDIT = "credit", "crédito"

    class Status(models.TextChoices):
        ACTIVE = "active", "activa"
        BLOCKED = "blocked", "bloqueada"
        EXPIRED = "expired", "vencida"
        CANCELLED = "cancelled", "cancelada"

    user = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="cards", db_column="usuario_id"
    )
    # Débito: cuenta de la que se descuenta. Crédito: cuenta de pago (opcional).
    account = models.ForeignKey(
        "banking.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cards",
        db_column="cuenta_id",
    )
    kind = models.CharField(max_length=8, choices=Kind.choices, db_column="tipo")
    brand = models.CharField(max_length=20, default="Visa", db_column="marca")
    token = models.CharField("token de la tarjeta", max_length=64, unique=True, db_column="token")
    last4 = models.CharField("últimos 4 dígitos", max_length=4, db_column="ultimos4")
    holder_name = models.CharField(max_length=150, db_column="nombre_titular")
    expiry_month = models.PositiveSmallIntegerField(db_column="mes_vencimiento")
    expiry_year = models.PositiveSmallIntegerField(db_column="anio_vencimiento")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE, db_column="estado"
    )
    credit_limit = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True, db_column="linea_credito"
    )
    daily_limit = models.DecimalField(
        max_digits=14, decimal_places=2, default=2000, db_column="limite_diario"
    )
    online_purchases_enabled = models.BooleanField(
        default=True, db_column="compras_internet_habilitadas"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")

    class Meta:
        db_table = "tarjeta"
        verbose_name = "tarjeta"
        verbose_name_plural = "tarjetas"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expiry_month__gte=1, expiry_month__lte=12),
                name="tarjeta_mes_vencimiento_1_12",
            ),
            models.CheckConstraint(
                condition=models.Q(daily_limit__gte=0), name="tarjeta_limite_diario_gte_0"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.brand} {self.kind} ****{self.last4}"


class CardTransaction(models.Model):
    """Consumo u operación hecha con una tarjeta."""

    class Status(models.TextChoices):
        AUTHORIZED = "authorized", "autorizada"
        SETTLED = "settled", "liquidada"
        DECLINED = "declined", "rechazada"
        REVERSED = "reversed", "revertida"

    card = models.ForeignKey(
        Card, on_delete=models.PROTECT, related_name="transactions", db_column="tarjeta_id"
    )
    # Movimiento de cuenta que generó el consumo (solo cuando se liquida).
    account_transaction = models.OneToOneField(
        "banking.Transaction",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="card_transaction",
        db_column="movimiento_id",
    )
    merchant = models.CharField("comercio", max_length=120, db_column="comercio")
    amount = models.DecimalField(max_digits=14, decimal_places=2, db_column="monto")
    currency = models.CharField(max_length=3, default="PEN", db_column="moneda")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.AUTHORIZED, db_column="estado"
    )
    authorization_code = models.CharField(
        max_length=12, blank=True, default="", db_column="codigo_autorizacion"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")

    class Meta:
        db_table = "consumo_tarjeta"
        verbose_name = "consumo con tarjeta"
        verbose_name_plural = "consumos con tarjeta"
        indexes = [models.Index(fields=["card", "created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="consumo_tarjeta_monto_gt_0"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.card_id} {self.merchant} {self.amount} [{self.status}]"
