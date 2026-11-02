"""Modelo v3: el desembolso y el pago de cuotas apuntan a `transaccion`."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("banking", "0003_transaccion"),
        ("loans", "0001_modelo_completo_es"),
    ]

    operations = [
        migrations.AddField(
            model_name="loan",
            name="disbursement_transaction",
            field=models.OneToOneField(
                blank=True,
                db_column="transaccion_desembolso_id",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="disbursed_loan",
                to="banking.transaction",
            ),
        ),
        migrations.RemoveField(
            model_name="loaninstallment",
            name="payment_transaction",
        ),
        migrations.AddField(
            model_name="loaninstallment",
            name="payment_transaction",
            field=models.OneToOneField(
                blank=True,
                db_column="transaccion_pago_id",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="loan_installment",
                to="banking.transaction",
            ),
        ),
    ]
