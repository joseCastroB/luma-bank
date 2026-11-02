"""Modelos de operaciones bancarias: cuentas, transacciones y beneficiarios."""

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


class Transaction(models.Model):
    """
    Operación de dinero: unifica transferencias y movimientos de cuenta.

    Abono (depósito, desembolso): solo `destination_account`.
    Cargo (consumo, pago de cuota): solo `source_account`.
    Entre cuentas de Luma Bank: ambas cuentas.
    Interbancaria: `source_account` y los campos `external_destination_*`.

    `amount` siempre es positivo; el sentido lo dan las cuentas. Una operación
    completada no se edita: un error se corrige con un extorno.
    """

    class Kind(models.TextChoices):
        DEPOSIT = "deposit", "depósito"
        WITHDRAWAL = "withdrawal", "retiro"
        OWN_TRANSFER = "own_transfer", "transferencia entre cuentas propias"
        THIRD_PARTY_TRANSFER = "third_party_transfer", "transferencia a terceros"
        INTERBANK_TRANSFER = "interbank_transfer", "transferencia interbancaria"
        CURRENCY_EXCHANGE = "currency_exchange", "conversión de moneda"
        CARD_PURCHASE = "card_purchase", "consumo con tarjeta"
        LOAN_DISBURSEMENT = "loan_disbursement", "desembolso de préstamo"
        LOAN_PAYMENT = "loan_payment", "pago de cuota"
        FEE = "fee", "comisión"
        INTEREST = "interest", "interés"
        REVERSAL = "reversal", "extorno"

    class Status(models.TextChoices):
        PENDING = "pending", "pendiente"
        COMPLETED = "completed", "completada"
        FAILED = "failed", "fallida"
        REVERSED = "reversed", "revertida"

    operation_code = models.CharField(
        "código de operación", max_length=20, unique=True, db_column="codigo_operacion"
    )
    kind = models.CharField(max_length=30, choices=Kind.choices, db_column="tipo")
    source_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="outgoing_transactions",
        db_column="cuenta_origen_id",
    )
    destination_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incoming_transactions",
        db_column="cuenta_destino_id",
    )
    external_destination_number = models.CharField(  # noqa: DJ001 (NULL segun el modelo v3)
        "cuenta o CCI destino",
        max_length=20,
        null=True,
        blank=True,
        db_column="numero_destino_externo",
    )
    external_destination_holder = models.CharField(  # noqa: DJ001 (NULL segun el modelo v3)
        max_length=150, null=True, blank=True, db_column="titular_destino_externo"
    )
    external_destination_bank = models.CharField(  # noqa: DJ001 (NULL segun el modelo v3)
        max_length=80, null=True, blank=True, db_column="banco_destino_externo"
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
    source_balance_after = models.DecimalField(
        "saldo resultante de origen",
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        db_column="saldo_origen_resultante",
    )
    destination_balance_after = models.DecimalField(
        "saldo resultante de destino",
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        db_column="saldo_destino_resultante",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")
    completed_at = models.DateTimeField(null=True, blank=True, db_column="fecha_completada")

    class Meta:
        db_table = "transaccion"
        verbose_name = "transacción"
        verbose_name_plural = "transacciones"
        indexes = [
            models.Index(fields=["source_account", "created_at"], name="transaccion_origen_fecha"),
            models.Index(
                fields=["destination_account", "created_at"], name="transaccion_destino_fecha"
            ),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="transaccion_monto_gt_0"),
            models.CheckConstraint(
                condition=models.Q(fee__gte=0), name="transaccion_comision_gte_0"
            ),
            models.CheckConstraint(
                condition=~models.Q(source_account=models.F("destination_account")),
                name="transaccion_cuentas_distintas",
            ),
            models.CheckConstraint(
                condition=models.Q(source_account__isnull=False)
                | models.Q(destination_account__isnull=False),
                name="transaccion_con_alguna_cuenta",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.operation_code} {self.amount} {self.currency} [{self.status}]"
