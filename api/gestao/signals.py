from django.contrib.auth.models import User
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver


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
