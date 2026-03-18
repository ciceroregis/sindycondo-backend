from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gestao', '0014_visitante_aprovado_por'),
    ]

    operations = [
        migrations.CreateModel(
            name='PushSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('endpoint', models.TextField(unique=True)),
                ('p256dh', models.TextField()),
                ('auth', models.TextField()),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='push_subscriptions',
                    to='gestao.usuario',
                )),
            ],
            options={
                'verbose_name': 'Push Subscription',
                'verbose_name_plural': 'Push Subscriptions',
                'db_table': 'push_subscriptions',
            },
        ),
    ]
