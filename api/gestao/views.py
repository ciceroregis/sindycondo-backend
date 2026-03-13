from django.utils import timezone

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db.models import F

from .models import Condominio, Garagem, Usuario, Visitante, RegistroAcesso
from .permissions import IsAdmin, IsAdminOrSindico, IsMesmoCondominio, IsPorteiroOrAbove
from .serializers import (
    CondominioSerializer,
    GaragemSerializer,
    UsuarioSerializer,
    UsuarioListSerializer,
    UsuarioUpdateSerializer,
    VisitanteSerializer,
    VisitanteListSerializer,
    RegistroAcessoSerializer,
    ValidarQRSerializer,
)


def _get_usuario(user):
    try:
        return user.usuario
    except Exception:
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    usuario = _get_usuario(request.user)
    if not usuario or not usuario.condominio:
        return Response({'detail': 'Perfil não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    condominio = usuario.condominio
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)

    moradores_qs = Usuario.objects.filter(condominio=condominio, tipo='morador', ativo=True)
    total_moradores = moradores_qs.count()
    moradores_mes = moradores_qs.filter(created_at__date__gte=inicio_mes).count()

    total_vagas = Garagem.objects.filter(condominio=condominio).count()
    vagas_disponiveis = Garagem.objects.filter(condominio=condominio, morador__isnull=True).count()

    visitantes_hoje = Visitante.objects.filter(
        condominio=condominio,
        data_inicio__date__lte=hoje,
        data_fim__date__gte=hoje,
    ).count()

    acessos_qs = RegistroAcesso.objects.filter(condominio=condominio, timestamp__date=hoje)
    total_acessos_hoje = acessos_qs.count()
    acessos_negados_hoje = acessos_qs.filter(autorizado=False).count()

    visitantes_pendentes = Visitante.objects.filter(condominio=condominio, status='pending').count()

    return Response({
        'total_moradores': total_moradores,
        'moradores_mes': moradores_mes,
        'total_vagas': total_vagas,
        'vagas_disponiveis': vagas_disponiveis,
        'total_visitantes_hoje': visitantes_hoje,
        'total_acessos_hoje': total_acessos_hoje,
        'acessos_negados_hoje': acessos_negados_hoje,
        'visitantes_pendentes': visitantes_pendentes,
    })


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

    def perform_update(self, serializer):
        old_total_vagas = serializer.instance.total_vagas or 0
        instance = serializer.save()
        new_total_vagas = instance.total_vagas or 0

        if new_total_vagas > old_total_vagas:
            # Descobre os números já cadastrados
            existentes = set(
                Garagem.objects.filter(condominio=instance).values_list('numero', flat=True)
            )
            criadas = 0
            numero = 1
            while criadas < (new_total_vagas - old_total_vagas):
                num_str = str(numero)
                if num_str not in existentes:
                    Garagem.objects.create(condominio=instance, numero=num_str)
                    existentes.add(num_str)
                    criadas += 1
                numero += 1

    def perform_create(self, serializer):
        instance = serializer.save()
        total_vagas = instance.total_vagas or 0
        for i in range(1, total_vagas + 1):
            Garagem.objects.create(condominio=instance, numero=str(i))


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

    def perform_destroy(self, instance):
        if instance.morador_id is not None:
            raise serializers.ValidationError(
                f'A garagem {instance.numero} está ocupada por {instance.morador.nome}. '
                f'Retire o morador da vaga antes de excluí-la.'
            )
        instance.delete()


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
            return Usuario.objects.select_related('condominio').prefetch_related('garagens').all()
        usuario = _get_usuario(user)
        if not usuario:
            return Usuario.objects.none()
        if usuario.tipo == 'admin':
            return Usuario.objects.select_related('condominio').prefetch_related('garagens').all()
        if usuario.tipo in ['sindico', 'porteiro']:
            return Usuario.objects.select_related('condominio').prefetch_related('garagens').filter(
                condominio=usuario.condominio
            )
        # morador: apenas si mesmo
        return Usuario.objects.prefetch_related('garagens').filter(id=usuario.id)

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
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = UsuarioListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
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


# ─── Fase 2: Visitantes ──────────────────────────────────────────────────────

class VisitanteViewSet(viewsets.ModelViewSet):
    """
    CRUD de visitantes com fluxo de aprovação e geração de QR Code.

    Fluxo:
      1. Morador cria visitante → status 'pending' (sem QR ainda)
      2. Síndico/Admin aprova → status 'approved' + QR gerado automaticamente
      3. Morador pode bloquear a qualquer momento → status 'blocked'

    Visibilidade:
      - admin/superuser → todos os visitantes
      - sindico/porteiro → apenas o condomínio deles
      - morador → apenas os próprios visitantes
    """

    def get_serializer_class(self):
        # Lista retorna versão resumida (sem foto e QR para economizar banda)
        if self.action == 'list':
            return VisitanteListSerializer
        return VisitanteSerializer

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdminOrSindico()]
        if self.action == 'aprovar':
            return [IsAdminOrSindico()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        usuario = _get_usuario(user)
        if not usuario:
            return Visitante.objects.none()

        # Expira visitantes com data_fim ultrapassada antes de retornar a lista.
        # Solução simples e sem Celery — válida para a Fase 2.
        Visitante.objects.filter(
            condominio=usuario.condominio,
            data_fim__lt=timezone.now(),
            status__in=['pending', 'approved'],
        ).update(status='expired')

        base_qs = Visitante.objects.select_related('morador', 'condominio')

        if user.is_superuser or usuario.tipo == 'admin':
            return base_qs.all()

        if usuario.tipo in ['sindico', 'porteiro']:
            return base_qs.filter(condominio=usuario.condominio)

        # morador: apenas os próprios visitantes
        return base_qs.filter(morador=usuario)

    def perform_create(self, serializer):
        """
        Injeta morador e condomínio automaticamente a partir do usuário logado.
        O morador não pode criar visitante para outro morador.
        """
        usuario = _get_usuario(self.request.user)
        if not usuario or not usuario.condominio:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Você precisa estar vinculado a um condomínio.')
        serializer.save(
            morador=usuario,
            condominio=usuario.condominio,
            status='pending',
        )

    def perform_update(self, serializer):
        """Morador só pode editar os próprios visitantes."""
        usuario = _get_usuario(self.request.user)
        instance = self.get_object()
        if usuario and usuario.tipo == 'morador' and instance.morador_id != usuario.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Você só pode editar os seus próprios visitantes.')
        serializer.save()

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminOrSindico])
    def aprovar(self, request, pk=None):
        """
        Aprova um visitante pendente e gera o QR Code de acesso.

        O QR só é gerado neste momento (não no cadastro) para garantir que
        apenas visitantes aprovados tenham um QR válido.
        """
        from .services.qr_service import gerar_qr_code

        visitante = self.get_object()

        if visitante.status != 'pending':
            return Response(
                {'detail': 'Apenas visitantes com status "pendente" podem ser aprovados.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        visitante.status = 'approved'
        visitante.qr_code_imagem = gerar_qr_code(visitante)
        visitante.save()

        serializer = VisitanteSerializer(visitante)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def bloquear(self, request, pk=None):
        """
        Bloqueia um visitante.

        - Morador: só pode bloquear os próprios visitantes.
        - Síndico/Admin: pode bloquear qualquer visitante do condomínio.
        """
        visitante = self.get_object()
        usuario = _get_usuario(request.user)

        if usuario and usuario.tipo == 'morador' and visitante.morador_id != usuario.id:
            return Response(
                {'detail': 'Você só pode bloquear os seus próprios visitantes.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        visitante.status = 'blocked'
        visitante.save(update_fields=['status'])
        return Response({'detail': 'Visitante bloqueado com sucesso.'})


# ─── Fase 2: Registros de Acesso ─────────────────────────────────────────────

class RegistroAcessoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Histórico de registros de acesso (somente leitura).

    A portaria NÃO cria registros manualmente aqui — ela usa o endpoint
    'validar_qr' que centraliza toda a lógica de validação e logging.

    Filtros disponíveis via query params:
      ?data=YYYY-MM-DD    → filtra por data
      ?autorizado=false   → somente acessos negados
      ?visitante_id=X     → registros de um visitante específico
    """
    serializer_class = RegistroAcessoSerializer
    permission_classes = [IsPorteiroOrAbove]

    def get_queryset(self):
        usuario = _get_usuario(self.request.user)
        if not usuario or not usuario.condominio:
            return RegistroAcesso.objects.none()

        qs = RegistroAcesso.objects.select_related(
            'visitante', 'porteiro', 'condominio'
        ).filter(condominio=usuario.condominio)

        # Filtro por data (ex: ?data=2025-03-13)
        data_param = self.request.query_params.get('data')
        if data_param:
            qs = qs.filter(timestamp__date=data_param)

        # Filtro por autorizado (ex: ?autorizado=false)
        autorizado_param = self.request.query_params.get('autorizado')
        if autorizado_param is not None:
            qs = qs.filter(autorizado=(autorizado_param.lower() == 'true'))

        # Filtro por visitante (ex: ?visitante_id=42)
        visitante_id = self.request.query_params.get('visitante_id')
        if visitante_id:
            qs = qs.filter(visitante_id=visitante_id)

        return qs


@api_view(['POST'])
@permission_classes([IsPorteiroOrAbove])
def validar_qr(request):
    """
    Valida o QR Code escaneado pela portaria e registra a tentativa de acesso.

    Recebe:
      - qr_code_id: UUID do QR Code
      - tipo_registro: 'entrada' ou 'saida'
      - placa_detectada (opcional): placa lida pela câmera
      - imagem_snapshot (opcional): foto da câmera no momento do acesso

    Retorna SEMPRE HTTP 200. A decisão (liberar ou bloquear) está no campo
    'autorizado' da resposta — nunca em um código de erro HTTP.

    Isso reflete como sistemas reais de portaria funcionam: um scan
    sempre recebe uma resposta, seja ela positiva ou negativa.

    Todo scan (aprovado ou negado) gera um RegistroAcesso para auditoria.
    """
    serializer = ValidarQRSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    porteiro = _get_usuario(request.user)
    dados = serializer.validated_data
    qr_code_id = dados['qr_code_id']
    tipo_registro = dados['tipo_registro']

    def _registrar_acesso(visitante, autorizado, motivo=''):
        """Helper interno para criar o RegistroAcesso sem repetir código."""
        return RegistroAcesso.objects.create(
            condominio=porteiro.condominio,
            visitante=visitante,
            porteiro=porteiro,
            tipo_acesso='qr',
            tipo_registro=tipo_registro,
            autorizado=autorizado,
            motivo_negado=motivo,
            placa_detectada=dados.get('placa_detectada', ''),
            imagem_snapshot=dados.get('imagem_snapshot'),
        )

    def _resposta_negada(registro, motivo):
        return Response({
            'autorizado': False,
            'motivo_negado': motivo,
            'visitante': None,
            'registro_id': registro.id,
        })

    # 1. Busca o visitante pelo UUID do QR
    try:
        visitante = Visitante.objects.select_related('morador', 'condominio').get(
            qr_code_id=qr_code_id
        )
    except Visitante.DoesNotExist:
        registro = _registrar_acesso(None, False, 'QR Code inválido')
        return _resposta_negada(registro, 'QR Code inválido')

    # 2. O QR pertence a este condomínio?
    if visitante.condominio_id != porteiro.condominio_id:
        registro = _registrar_acesso(visitante, False, 'QR Code de outro condomínio')
        return _resposta_negada(registro, 'QR Code de outro condomínio')

    # 3. Verifica o status do visitante
    MENSAGENS_STATUS = {
        'blocked': 'Visitante bloqueado',
        'pending': 'Visita aguardando aprovação',
        'expired': 'QR Code expirado',
    }
    if visitante.status in MENSAGENS_STATUS:
        motivo = MENSAGENS_STATUS[visitante.status]
        registro = _registrar_acesso(visitante, False, motivo)
        return _resposta_negada(registro, motivo)

    # 4. Verifica janela de tempo autorizada
    agora = timezone.now()
    if not (visitante.data_inicio <= agora <= visitante.data_fim):
        motivo = 'Fora do período autorizado'
        registro = _registrar_acesso(visitante, False, motivo)
        return _resposta_negada(registro, motivo)

    # 5. Verifica limite de pessoas (apenas para entrada)
    if tipo_registro == 'entrada' and visitante.usos_count >= visitante.max_pessoas:
        motivo = 'Limite de pessoas atingido'
        registro = _registrar_acesso(visitante, False, motivo)
        return _resposta_negada(registro, motivo)

    # ─── ACESSO AUTORIZADO ──────────────────────────────────────────────────
    # Usa F() para incrementar o contador de forma atômica (thread-safe).
    # Isso evita o problema de dois porteiros aprovarem a última vaga ao mesmo tempo.
    if tipo_registro == 'entrada':
        Visitante.objects.filter(pk=visitante.pk).update(
            usos_count=F('usos_count') + 1
        )
        visitante.refresh_from_db(fields=['usos_count'])

    registro = _registrar_acesso(visitante, True)

    return Response({
        'autorizado': True,
        'motivo_negado': '',
        'visitante': {
            'id': visitante.id,
            'nome': visitante.nome,
            'morador_nome': visitante.morador.nome if visitante.morador else None,
            'apartamento': visitante.morador.apartamento if visitante.morador else None,
            'bloco': visitante.morador.bloco if visitante.morador else None,
            'data_inicio': visitante.data_inicio,
            'data_fim': visitante.data_fim,
            'usos_count': visitante.usos_count,
            'max_pessoas': visitante.max_pessoas,
        },
        'registro_id': registro.id,
    })
