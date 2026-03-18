import json
import logging
import threading

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def garantir_perfil_usuario(sender, instance, created, **kwargs):
    """
    Após criação de um User, verifica se existe perfil Usuario correspondente.
    Se não existir (criação direta via admin/shell), deleta o User automaticamente.
    Superusers são ignorados.
    """
    if not created or instance.is_superuser:
        return

    def verificar_e_deletar():
        try:
            instance.usuario  # acessa o perfil — lança exceção se não existir
        except Exception:
            instance.delete()

    transaction.on_commit(verificar_e_deletar)


def _enviar_push_porteiros(visitante_id):
    """Envia push notification para porteiros do mesmo condomínio (executa em thread)."""
    try:
        from pywebpush import webpush, WebPushException
        from .models import Visitante, PushSubscription

        visitante = Visitante.objects.select_related('morador', 'condominio').get(pk=visitante_id)
        condominio = visitante.condominio
        morador_nome = visitante.morador.nome if visitante.morador else 'Morador'

        payload = json.dumps({
            'title': 'Novo Visitante Aguardando Aprovação',
            'body': f'{morador_nome} cadastrou {visitante.nome} — aprovação necessária.',
            'icon': '/icons/icon-192x192.png',
            'badge': '/icons/icon-72x72.png',
            'data': {'url': '/visitantes'},
        })

        subscriptions = PushSubscription.objects.filter(
            usuario__condominio=condominio,
            usuario__tipo__in=['admin', 'sindico', 'porteiro'],
            usuario__notificacoes_push=True,
        )

        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        'endpoint': sub.endpoint,
                        'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
                    },
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={'sub': f'mailto:{settings.VAPID_ADMIN_EMAIL}'},
                    content_encoding='aes128gcm',
                )
            except WebPushException as e:
                if e.response and e.response.status_code in (404, 410):
                    sub.delete()  # subscription expirada
                else:
                    logger.warning('Push falhou para %s: %s', sub.endpoint[:60], e)
    except Exception as e:
        logger.error('Erro ao enviar push notifications: %s', e)


@receiver(post_save, sender='gestao.Visitante')
def notificar_porteiros_novo_visitante(sender, instance, created, **kwargs):
    """Ao criar um visitante (status pending), notifica porteiros via push."""
    if not created:
        return

    def disparar():
        t = threading.Thread(target=_enviar_push_porteiros, args=(instance.pk,), daemon=True)
        t.start()

    transaction.on_commit(disparar)
