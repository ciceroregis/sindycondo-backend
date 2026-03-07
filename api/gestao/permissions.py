from rest_framework.permissions import BasePermission


def _get_usuario(user):
    try:
        return user.usuario
    except Exception:
        return None


class IsAdmin(BasePermission):
    """Apenas administradores do sistema (tipo='admin') ou superusers."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        usuario = _get_usuario(request.user)
        return usuario is not None and usuario.tipo == 'admin'


class IsAdminOrSindico(BasePermission):
    """Administradores e síndicos."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        usuario = _get_usuario(request.user)
        return usuario is not None and usuario.tipo in ['admin', 'sindico']


class IsPorteiroOrAbove(BasePermission):
    """Porteiros, síndicos e administradores."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        usuario = _get_usuario(request.user)
        return usuario is not None and usuario.tipo in ['admin', 'sindico', 'porteiro']


class IsMesmoCondominio(BasePermission):
    """Garante que o objeto pertence ao mesmo condomínio do usuário autenticado."""

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        usuario = _get_usuario(request.user)
        if not usuario:
            return False
        # Suporta objetos com campo 'condominio' ou o próprio Condominio
        condominio = getattr(obj, 'condominio', obj if hasattr(obj, 'blocos') else None)
        if condominio is None:
            return False
        condominio_id = getattr(condominio, 'id', condominio)
        return usuario.condominio_id == condominio_id