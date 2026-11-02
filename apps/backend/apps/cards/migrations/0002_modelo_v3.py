"""Modelo v3: los consumos apuntan a `transaccion` y la tarjeta guarda su saldo utilizado."""

import django.db.models.deletion
from django.db import migrations, models


def _codigos_vacios_a_null(apps, schema_editor):
    consumo = apps.get_model("cards", "CardTransaction")
    consumo.objects.filter(authorization_code="").update(authorization_code=None)


class Migration(migrations.Migration):
    dependencies = [
        ("banking", "0003_transaccion"),
        ("cards", "0001_modelo_completo_es"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="cardtransaction",
            name="account_transaction",
        ),
        migrations.AddField(
            model_name="cardtransaction",
            name="transaction",
            field=models.OneToOneField(
                blank=True,
                db_column="transaccion_id",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="card_transaction",
                to="banking.transaction",
            ),
        ),
        migrations.AddField(
            model_name="card",
            name="credit_used",
            field=models.DecimalField(
                blank=True,
                db_column="saldo_utilizado",
                decimal_places=2,
                max_digits=14,
                null=True,
                verbose_name="saldo utilizado",
            ),
        ),
        migrations.AlterField(
            model_name="cardtransaction",
            name="authorization_code",
            field=models.CharField(
                blank=True, db_column="codigo_autorizacion", max_length=12, null=True
            ),
        ),
        migrations.RunPython(_codigos_vacios_a_null, migrations.RunPython.noop),
    ]
