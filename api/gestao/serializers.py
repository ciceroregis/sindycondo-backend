import unicodedata

from rest_framework import serializers

from .models import Condominio, Usuario, Visitante, RegistroAcesso


def _gerar_username(nome, apartamento=None):
    """
    Gera username a partir do primeiro e último nome + apartamento.
    Ex: "João da Silva", apto 101 → "joao.silva.101"
    Ex: "João da Silva", sem apto → "joao.silva"
    Se já existir, adiciona contador: "joao.silva.101.2"...
    """
    partes = nome.strip().split()
    primeiro = partes[0] if partes else 'usuario'
    ultimo = partes[-1] if len(partes) > 1 else ''

    def normalizar(texto):
        sem_acento = unicodedata.normalize('NFKD', texto)
        sem_acento = ''.join(c for c in sem_acento if not unicodedata.combining(c))
        return sem_acento.lower()

    base = normalizar(primeiro)
    if ultimo:
        base = f'{base}.{normalizar(ultimo)}'

    if apartamento:
        base = f'{base}.{apartamento}'

    username = base
    contador = 2
    while Usuario.objects.filter(username=username).exists():
        username = f'{base}.{contador}'
        contador += 1

    return username


class CondominioSerializer(serializers.ModelSerializer):
    total_usuarios = serializers.SerializerMethodField()

    class Meta:
        model = Condominio
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def get_total_usuarios(self, obj):
        return obj.usuarios.filter(ativo=True).count()


class UsuarioListSerializer(serializers.ModelSerializer):
    """Versão resumida para listagens"""
    condominio_nome = serializers.CharField(source='condominio.nome', read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'nome','email', 'cpf', 'tipo', 'apartamento', 'bloco',
            'condominio', 'condominio_nome', 'telefone', 'ativo',
        ]


class UsuarioSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    condominio_nome = serializers.CharField(source='condominio.nome', read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email',
            'nome', 'cpf', 'condominio', 'condominio_nome', 'tipo', 'telefone',
            'apartamento', 'bloco', 'foto', 'face_embeddings',
            'notificacoes_push', 'notificacoes_whatsapp', 'ativo',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['username', 'face_embeddings', 'created_at', 'updated_at']

    def validate_email(self, value):
        qs = Usuario.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Este e-mail já está cadastrado.')
        return value.lower()

    def create(self, validated_data):
        cpf_digits = ''.join(filter(str.isdigit, validated_data.get('cpf', '')))
        apartamento = validated_data.get('apartamento', '')
        password = f'{cpf_digits}{apartamento}'
        validated_data['username'] = _gerar_username(validated_data.get('nome', ''), apartamento)
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    """Campos que o próprio morador pode atualizar no seu perfil."""

    class Meta:
        model = Usuario
        fields = [
            'email', 'nome',
            'telefone', 'foto', 'notificacoes_push', 'notificacoes_whatsapp',
        ]

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class VisitanteSerializer(serializers.ModelSerializer):
    morador_nome = serializers.CharField(source='morador.nome', read_only=True)

    class Meta:
        model = Visitante
        fields = '__all__'
        read_only_fields = ['qr_code_id', 'qr_code_imagem', 'usos_count', 'created_at']


class RegistroAcessoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroAcesso
        fields = '__all__'
        read_only_fields = ['timestamp']