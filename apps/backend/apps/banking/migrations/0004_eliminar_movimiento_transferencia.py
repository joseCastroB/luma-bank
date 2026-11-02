"""Modelo v3: elimina `movimiento` y `transferencia`, ya sin referencias."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("banking", "0003_transaccion"),
        ("cards", "0002_modelo_v3"),
        ("loans", "0002_modelo_v3"),
    ]

    operations = [
        migrations.DeleteModel(name="MovimientoLegado"),
        migrations.DeleteModel(name="Transfer"),
    ]
