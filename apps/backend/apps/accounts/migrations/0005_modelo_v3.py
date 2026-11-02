"""Modelo v3: validaciones de DNI ligadas al usuario, notificaciones a `transaccion`."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _secretos_vacios_a_null(apps, schema_editor):
    usuario = apps.get_model("accounts", "User")
    usuario.objects.filter(totp_secret_encrypted="").update(totp_secret_encrypted=None)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_modelo_completo_es"),
        ("banking", "0003_transaccion"),
    ]

    operations = [
        migrations.AddField(
            model_name="dnivalidationlog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                db_column="usuario_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="dni_validations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="dnivalidationlog",
            name="dni",
            field=models.CharField(db_column="dni", max_length=8),
        ),
        migrations.AddField(
            model_name="notification",
            name="transaction",
            field=models.ForeignKey(
                blank=True,
                db_column="transaccion_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="notifications",
                to="banking.transaction",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="totp_secret_encrypted",
            field=models.CharField(
                blank=True, db_column="secreto_totp_cifrado", max_length=255, null=True
            ),
        ),
        migrations.RunPython(_secretos_vacios_a_null, migrations.RunPython.noop),
    ]
