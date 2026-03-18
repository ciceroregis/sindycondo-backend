"""
Migration: adiciona o campo tipo_registro em RegistroAcesso.

Este campo diferencia registros de ENTRADA de registros de SAÍDA,
essencial para o histórico de acesso da portaria.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestao", "0012_garagem_tipo_matricula_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="registroacesso",
            name="tipo_registro",
            field=models.CharField(
                choices=[("entrada", "Entrada"), ("saida", "Saída")],
                default="entrada",
                max_length=10,
            ),
        ),
    ]
