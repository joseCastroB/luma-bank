"""Modelos de préstamos personales y su cronograma de cuotas."""

from __future__ import annotations

from django.db import models


class Loan(models.Model):
    """Préstamo personal solicitado por un cliente."""

    class Status(models.TextChoices):
        REQUESTED = "requested", "solicitado"
        APPROVED = "approved", "aprobado"
        REJECTED = "rejected", "rechazado"
        DISBURSED = "disbursed", "desembolsado"
        PAID = "paid", "pagado"
        DEFAULTED = "defaulted", "en mora"

    user = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="loans", db_column="usuario_id"
    )
    # Cuenta donde se abona el préstamo y de donde se cobran las cuotas.
    account = models.ForeignKey(
        "banking.Account", on_delete=models.PROTECT, related_name="loans", db_column="cuenta_id"
    )
    principal = models.DecimalField(
        "monto solicitado", max_digits=14, decimal_places=2, db_column="monto_solicitado"
    )
    annual_rate = models.DecimalField(
        "TEA (%)", max_digits=5, decimal_places=2, db_column="tasa_anual"
    )
    term_months = models.PositiveSmallIntegerField("plazo en meses", db_column="plazo_meses")
    monthly_payment = models.DecimalField(
        "cuota mensual", max_digits=14, decimal_places=2, db_column="cuota_mensual"
    )
    outstanding_balance = models.DecimalField(
        "saldo pendiente", max_digits=14, decimal_places=2, db_column="saldo_pendiente"
    )
    currency = models.CharField(max_length=3, default="PEN", db_column="moneda")
    purpose = models.CharField("motivo", max_length=140, blank=True, default="", db_column="motivo")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.REQUESTED, db_column="estado"
    )
    requested_at = models.DateTimeField(auto_now_add=True, db_column="fecha_solicitud")
    decided_at = models.DateTimeField(null=True, blank=True, db_column="fecha_decision")
    disbursed_at = models.DateTimeField(null=True, blank=True, db_column="fecha_desembolso")

    class Meta:
        db_table = "prestamo"
        verbose_name = "préstamo"
        verbose_name_plural = "préstamos"
        constraints = [
            models.CheckConstraint(condition=models.Q(principal__gt=0), name="prestamo_monto_gt_0"),
            models.CheckConstraint(
                condition=models.Q(annual_rate__gte=0), name="prestamo_tasa_anual_gte_0"
            ),
            models.CheckConstraint(
                condition=models.Q(term_months__gte=1), name="prestamo_plazo_meses_gte_1"
            ),
            models.CheckConstraint(
                condition=models.Q(outstanding_balance__gte=0),
                name="prestamo_saldo_pendiente_gte_0",
            ),
        ]

    def __str__(self) -> str:
        return f"Préstamo {self.pk} {self.principal} {self.currency} [{self.status}]"


class LoanInstallment(models.Model):
    """Cuota del cronograma de pagos de un préstamo."""

    class Status(models.TextChoices):
        PENDING = "pending", "pendiente"
        PAID = "paid", "pagada"
        OVERDUE = "overdue", "vencida"

    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name="installments", db_column="prestamo_id"
    )
    number = models.PositiveSmallIntegerField("número de cuota", db_column="numero")
    due_date = models.DateField("fecha de vencimiento", db_column="fecha_vencimiento")
    principal_amount = models.DecimalField(
        "amortización", max_digits=14, decimal_places=2, db_column="amortizacion"
    )
    interest_amount = models.DecimalField(
        "interés", max_digits=14, decimal_places=2, db_column="interes"
    )
    total_amount = models.DecimalField(
        "total de la cuota", max_digits=14, decimal_places=2, db_column="total"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_column="estado"
    )
    paid_at = models.DateTimeField(null=True, blank=True, db_column="fecha_pago")
    # Movimiento de cuenta con el que se pagó la cuota.
    payment_transaction = models.OneToOneField(
        "banking.Transaction",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="loan_installment",
        db_column="movimiento_pago_id",
    )

    class Meta:
        db_table = "cuota_prestamo"
        verbose_name = "cuota"
        verbose_name_plural = "cuotas"
        ordering = ["loan", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["loan", "number"], name="cuota_prestamo_prestamo_numero_unico"
            ),
            models.CheckConstraint(
                condition=models.Q(total_amount__gt=0), name="cuota_prestamo_total_gt_0"
            ),
        ]

    def __str__(self) -> str:
        return f"Cuota {self.number} del préstamo {self.loan_id} [{self.status}]"
