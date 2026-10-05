"""Modelos de operaciones bancarias: cuentas, movimientos, transferencias y beneficiarios."""

from __future__ import annotations

from django.db import models


class Account(models.Model):
    """Cuenta bancaria de un cliente."""

    class Kind(models.TextChoices):
        SAVINGS = "savings", "ahorros"
        CHECKING = "checking", "corriente"

    class Status(models.TextChoices):
        ACTIVE = "active", "activa"
        FROZEN = "frozen", "congelada"
        CLOSED = "closed", "cerrada"

    user = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="accounts", db_column="usuario_id"
    )
    number = models.CharField("número de cuenta", max_length=20, unique=True, db_column="numero")
    kind = models.CharField(
        max_length=16, choices=Kind.choices, default=Kind.SAVINGS, db_column="tipo"
    )
    currency = models.CharField(max_length=3, default="PEN", db_column="moneda")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE, db_column="estado"
    )
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0, db_column="saldo")
    opened_at = models.DateTimeField(auto_now_add=True, db_column="fecha_apertura")

    class Meta:
        db_table = "cuenta"
        verbose_name = "cuenta"
        verbose_name_plural = "cuentas"

    def __str__(self) -> str:
        return f"{self.number} ({self.user_id})"


class Beneficiary(models.Model):
    """Destinatario frecuente guardado por el cliente para sus transferencias."""

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="beneficiaries",
        db_column="usuario_id",
    )
    alias = models.CharField(max_length=60, db_column="alias")
    holder_name = models.CharField("titular", max_length=150, db_column="nombre_titular")
    account_number = models.CharField(
        "cuenta o CCI destino", max_length=20, db_column="numero_cuenta"
    )
    bank_name = models.CharField(max_length=80, default="Luma Bank", db_column="banco")
    created_at = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")

    class Meta:
        db_table = "beneficiario"
        verbose_name = "beneficiario"
        verbose_name_plural = "beneficiarios"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "account_number"], name="beneficiario_usuario_cuenta_unico"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.alias} ({self.account_number})"


class Transfer(models.Model):
    """
    Transferencia de dinero ordenada por un cliente.

    Interna: `destination_account` apunta a otra cuenta de Luma Bank.
    Interbancaria: `destination_account` queda en NULL y se llenan los campos
    `destination_*` externos.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "pendiente"
        COMPLETED = "completed", "completada"
        FAILED = "failed", "fallida"
        REVERSED = "reversed", "revertida"

    operation_code = models.CharField(
        "código de operación", max_length=20, unique=True, db_column="codigo_operacion"
    )
    source_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="transfers_sent",
        db_column="cuenta_origen_id",
    )
    destination_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transfers_received",
        db_column="cuenta_destino_id",
    )
    destination_number = models.CharField(
        "cuenta o CCI destino", max_length=20, db_column="numero_destino"
    )
    destination_holder = models.CharField(
        max_length=150, blank=True, default="", db_column="titular_destino"
    )
    destination_bank = models.CharField(
        max_length=80, default="Luma Bank", db_column="banco_destino"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2, db_column="monto")
    fee = models.DecimalField(
        "comisión", max_digits=14, decimal_places=2, default=0, db_column="comision"
    )
    currency = models.CharField(max_length=3, default="PEN", db_column="moneda")
    concept = models.CharField(max_length=140, blank=True, default="", db_column="concepto")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_column="estado"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")
    completed_at = models.DateTimeField(null=True, blank=True, db_column="fecha_completada")

    class Meta:
        db_table = "transferencia"
        verbose_name = "transferencia"
        verbose_name_plural = "transferencias"
        indexes = [models.Index(fields=["source_account", "created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="transferencia_monto_gt_0"
            ),
            models.CheckConstraint(
                condition=models.Q(fee__gte=0), name="transferencia_comision_gte_0"
            ),
            models.CheckConstraint(
                condition=~models.Q(source_account=models.F("destination_account")),
                name="transferencia_cuentas_distintas",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.operation_code} {self.amount} {self.currency} [{self.status}]"


class Transaction(models.Model):
    """
    Movimiento de una cuenta (libro mayor). Es de solo inserción: nunca se
    edita ni se borra; un error se corrige con un movimiento inverso.

    `amount` siempre es positivo; el sentido lo da `direction`.
    """

    class Direction(models.TextChoices):
        CREDIT = "credit", "abono"
        DEBIT = "debit", "cargo"

    class Kind(models.TextChoices):
        DEPOSIT = "deposit", "depósito"
        WITHDRAWAL = "withdrawal", "retiro"
        TRANSFER = "transfer", "transferencia"
        CARD_PURCHASE = "card_purchase", "consumo con tarjeta"
        LOAN_DISBURSEMENT = "loan_disbursement", "desembolso de préstamo"
        LOAN_PAYMENT = "loan_payment", "pago de cuota"
        FEE = "fee", "comisión"
        INTEREST = "interest", "interés"
        REVERSAL = "reversal", "extorno"

    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="transactions", db_column="cuenta_id"
    )
    direction = models.CharField(max_length=8, choices=Direction.choices, db_column="sentido")
    kind = models.CharField(max_length=24, choices=Kind.choices, db_column="tipo")
    amount = models.DecimalField(max_digits=14, decimal_places=2, db_column="monto")
    balance_after = models.DecimalField(
        "saldo resultante", max_digits=14, decimal_places=2, db_column="saldo_resultante"
    )
    description = models.CharField(max_length=140, blank=True, default="", db_column="descripcion")
    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transactions",
        db_column="transferencia_id",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")

    class Meta:
        db_table = "movimiento"
        verbose_name = "movimiento"
        verbose_name_plural = "movimientos"
        indexes = [models.Index(fields=["account", "created_at"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="movimiento_monto_gt_0"),
        ]

    def __str__(self) -> str:
        return f"{self.account_id} {self.direction} {self.amount} ({self.kind})"
