"""
Modelo v3: `transaccion` unifica `transferencia` y `movimiento`.

El modelo viejo `Transaction` se renombra a `MovimientoLegado` para liberar el
nombre; las tablas viejas se eliminan en 0004, cuando tarjetas, préstamos y
notificaciones ya apuntan a la tabla nueva.
"""

import django.db.models.deletion
from django.db import migrations, models


def _abortar_si_hay_datos(apps, schema_editor):
    """Nada escribía en estas tablas; si tienen filas, no se pierden en silencio."""
    for modelo in ("Transaction", "Transfer"):
        if apps.get_model("banking", modelo).objects.exists():
            raise RuntimeError(
                f"La tabla de banking.{modelo} tiene datos: pásalos a `transaccion` "
                "antes de aplicar esta migración."
            )


class Migration(migrations.Migration):
    dependencies = [
        ("banking", "0002_modelo_completo_es"),
        ("cards", "0001_modelo_completo_es"),
        ("loans", "0001_modelo_completo_es"),
    ]

    operations = [
        migrations.RunPython(_abortar_si_hay_datos, migrations.RunPython.noop),
        migrations.RenameModel(old_name="Transaction", new_name="MovimientoLegado"),
        migrations.CreateModel(
            name="Transaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "operation_code",
                    models.CharField(
                        db_column="codigo_operacion",
                        max_length=20,
                        unique=True,
                        verbose_name="código de operación",
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("deposit", "depósito"),
                            ("withdrawal", "retiro"),
                            ("own_transfer", "transferencia entre cuentas propias"),
                            ("third_party_transfer", "transferencia a terceros"),
                            ("interbank_transfer", "transferencia interbancaria"),
                            ("currency_exchange", "conversión de moneda"),
                            ("card_purchase", "consumo con tarjeta"),
                            ("loan_disbursement", "desembolso de préstamo"),
                            ("loan_payment", "pago de cuota"),
                            ("fee", "comisión"),
                            ("interest", "interés"),
                            ("reversal", "extorno"),
                        ],
                        db_column="tipo",
                        max_length=30,
                    ),
                ),
                (
                    "external_destination_number",
                    models.CharField(
                        blank=True,
                        db_column="numero_destino_externo",
                        max_length=20,
                        null=True,
                        verbose_name="cuenta o CCI destino",
                    ),
                ),
                (
                    "external_destination_holder",
                    models.CharField(
                        blank=True,
                        db_column="titular_destino_externo",
                        max_length=150,
                        null=True,
                    ),
                ),
                (
                    "external_destination_bank",
                    models.CharField(
                        blank=True,
                        db_column="banco_destino_externo",
                        max_length=80,
                        null=True,
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(db_column="monto", decimal_places=2, max_digits=14),
                ),
                (
                    "fee",
                    models.DecimalField(
                        db_column="comision",
                        decimal_places=2,
                        default=0,
                        max_digits=14,
                        verbose_name="comisión",
                    ),
                ),
                (
                    "currency",
                    models.CharField(db_column="moneda", default="PEN", max_length=3),
                ),
                (
                    "concept",
                    models.CharField(blank=True, db_column="concepto", default="", max_length=140),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "pendiente"),
                            ("completed", "completada"),
                            ("failed", "fallida"),
                            ("reversed", "revertida"),
                        ],
                        db_column="estado",
                        default="pending",
                        max_length=16,
                    ),
                ),
                (
                    "source_balance_after",
                    models.DecimalField(
                        blank=True,
                        db_column="saldo_origen_resultante",
                        decimal_places=2,
                        max_digits=14,
                        null=True,
                        verbose_name="saldo resultante de origen",
                    ),
                ),
                (
                    "destination_balance_after",
                    models.DecimalField(
                        blank=True,
                        db_column="saldo_destino_resultante",
                        decimal_places=2,
                        max_digits=14,
                        null=True,
                        verbose_name="saldo resultante de destino",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, db_column="fecha_creacion"),
                ),
                (
                    "completed_at",
                    models.DateTimeField(blank=True, db_column="fecha_completada", null=True),
                ),
                (
                    "source_account",
                    models.ForeignKey(
                        blank=True,
                        db_column="cuenta_origen_id",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="outgoing_transactions",
                        to="banking.account",
                    ),
                ),
                (
                    "destination_account",
                    models.ForeignKey(
                        blank=True,
                        db_column="cuenta_destino_id",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="incoming_transactions",
                        to="banking.account",
                    ),
                ),
            ],
            options={
                "verbose_name": "transacción",
                "verbose_name_plural": "transacciones",
                "db_table": "transaccion",
            },
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(
                fields=["source_account", "created_at"], name="transaccion_origen_fecha"
            ),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(
                fields=["destination_account", "created_at"], name="transaccion_destino_fecha"
            ),
        ),
        migrations.AddConstraint(
            model_name="transaction",
            constraint=models.CheckConstraint(
                condition=models.Q(("amount__gt", 0)), name="transaccion_monto_gt_0"
            ),
        ),
        migrations.AddConstraint(
            model_name="transaction",
            constraint=models.CheckConstraint(
                condition=models.Q(("fee__gte", 0)), name="transaccion_comision_gte_0"
            ),
        ),
        migrations.AddConstraint(
            model_name="transaction",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("source_account", models.F("destination_account")), _negated=True
                ),
                name="transaccion_cuentas_distintas",
            ),
        ),
        migrations.AddConstraint(
            model_name="transaction",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("source_account__isnull", False),
                    ("destination_account__isnull", False),
                    _connector="OR",
                ),
                name="transaccion_con_alguna_cuenta",
            ),
        ),
    ]
