from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Condominio, Usuario
from .permissions import IsAdmin, IsAdminOrSindico, IsMesmoCondominio
from .serializers import (
    CondominioSerializer,
    UsuarioSerializer,
    UsuarioListSerializer,
    UsuarioUpdateSerializer,
)


def _get_usuario(user):
    try:
        return user.usuario
    except Exception:
        return None


@api_view(['GET'])
def health_check(request):
    return Response({
        'status': 'SindyCondo API rodando!',
        'version': '1.0.0',
        'endpoints': [
            'GET  /api/health/',
            'POST /api/auth/login/',
            'POST /api/auth/refresh/',
            'POST /api/auth/logout/',
            'GET  /api/condominios/',
            'GET  /api/usuarios/',
            'GET  /api/usuarios/me/',
        ],
    })


class CondominioViewSet(viewsets.ModelViewSet):
    serializer_class = CondominioSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAdmin()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminOrSindico()]
        return [IsAuthenticated(), IsMesmoCondominio()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Condominio.objects.all()
        usuario = _get_usuario(user)
        if not usuario:
            return Condominio.objects.none()
        if usuario.tipo == 'admin':
            return Condominio.objects.all()
        if usuario.condominio:
            return Condominio.objects.filter(id=usuario.condominio_id)
        return Condominio.objects.none()


class UsuarioViewSet(viewsets.ModelViewSet):

    def get_serializer_class(self):
        if self.action == 'list':
            return UsuarioListSerializer
        return UsuarioSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAdminOrSindico()]
        if self.action == 'destroy':
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Usuario.objects.select_related('condominio').all()
        usuario = _get_usuario(user)
        if not usuario:
            return Usuario.objects.none()
        if usuario.tipo == 'admin':
            return Usuario.objects.select_related('condominio').all()
        if usuario.tipo in ['sindico', 'porteiro']:
            return Usuario.objects.select_related('condominio').filter(
                condominio=usuario.condominio
            )
        # morador: apenas si mesmo
        return Usuario.objects.filter(id=usuario.id)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        usuario = _get_usuario(request.user)
        if usuario and usuario.tipo == 'morador' and instance.id != usuario.id:
            return Response(
                {'detail': 'Sem permissão para editar outros usuários.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Retorna o perfil do usuário autenticado."""
        usuario = _get_usuario(request.user)
        if not usuario:
            return Response(
                {'detail': 'Perfil não encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = UsuarioSerializer(usuario)
        return Response(serializer.data)

    @action(detail=False, methods=['patch'], permission_classes=[IsAuthenticated])
    def me_update(self, request):
        """Atualiza o perfil do usuário autenticado (campos limitados para moradores)."""
        usuario = _get_usuario(request.user)
        if not usuario:
            return Response(
                {'detail': 'Perfil não encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        SerializerClass = (
            UsuarioUpdateSerializer if usuario.tipo == 'morador' else UsuarioSerializer
        )
        serializer = SerializerClass(usuario, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)