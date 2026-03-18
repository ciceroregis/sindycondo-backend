"""
Migration: registra quem liberou a entrada do visitante e quando.

O morador cadastra a visita, o síndico/admin aprova — mas o campo
'liberado_por' registra o porteiro/síndico que clicou em "aprovar"
(gerou o QR), permitindo auditoria em condomínios com múltiplos
operadores por turno.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestao", "0013_add_tipo_registro_acesso"),
    ]

    operations = [
        migrations.AddField(
            model_name="visitante",
            name="liberado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="visitantes_liberados",
                to="gestao.usuario",
            ),
        ),
        migrations.AddField(
            model_name="visitante",
            name="liberado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
