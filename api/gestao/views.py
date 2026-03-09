from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Condominio, Garagem, Usuario
from .permissions import IsAdmin, IsAdminOrSindico, IsMesmoCondominio
from .serializers import (
    CondominioSerializer,
    GaragemSerializer,
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
            'GET  /api/garagens/',
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


class GaragemViewSet(viewsets.ModelViewSet):
    serializer_class = GaragemSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrSindico()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Garagem.objects.select_related('condominio', 'morador').all()
        usuario = _get_usuario(user)
        if not usuario:
            return Garagem.objects.none()
        if usuario.tipo == 'admin':
            return Garagem.objects.select_related('condominio', 'morador').all()
        if usuario.condominio:
            qs = Garagem.objects.select_related('condominio', 'morador').filter(
                condominio=usuario.condominio
            )
            # Filtro opcional: ?disponivel=true
            if self.request.query_params.get('disponivel') == 'true':
                qs = qs.filter(morador__isnull=True)
            return qs
        return Garagem.objects.none()


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
        if self.action in ['update', 'partial_update']:
            return [IsAdminOrSindico()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Usuario.objects.select_related('condominio', 'garagem').all()
        usuario = _get_usuario(user)
        if not usuario:
            return Usuario.objects.none()
        if usuario.tipo == 'admin':
            return Usuario.objects.select_related('condominio', 'garagem').all()
        if usuario.tipo in ['sindico', 'porteiro']:
            return Usuario.objects.select_related('condominio', 'garagem').filter(
                condominio=usuario.condominio
            )
        # morador: apenas si mesmo
        return Usuario.objects.select_related('garagem').filter(id=usuario.id)

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

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrSindico])
    def pendentes(self, request):
        """Lista moradores pendentes de aprovação."""
        usuario = _get_usuario(request.user)
        qs = Usuario.objects.filter(is_active=False, tipo='morador')
        if usuario and usuario.tipo not in ['admin'] and not request.user.is_superuser:
            qs = qs.filter(condominio=usuario.condominio)
        serializer = UsuarioListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminOrSindico])
    def aprovar(self, request, pk=None):
        """Aprova cadastro de morador."""
        instance = self.get_object()
        instance.is_active = True
        instance.save(update_fields=['is_active'])
        return Response({'detail': 'Morador aprovado com sucesso.'})

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminOrSindico])
    def rejeitar(self, request, pk=None):
        """Rejeita cadastro de morador."""
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response({'detail': 'Morador rejeitado.'})
