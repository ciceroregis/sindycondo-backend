import unicodedata

from rest_framework import serializers

from .models import Condominio, Garagem, Usuario, Visitante, RegistroAcesso


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
    cnpj = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True, validators=[])

    class Meta:
        model = Condominio
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def get_total_usuarios(self, obj):
        return obj.usuarios.filter(ativo=True).count()

    def validate_cnpj(self, value):
        if self.instance:
            return self.instance.cnpj  # ignora o valor enviado, mantém o original
        if Condominio.objects.filter(cnpj=value).exists():
            raise serializers.ValidationError('Já existe um condomínio cadastrado com este CNPJ.')
        return value

    def validate(self, attrs):
        if not self.instance:
            return attrs

        total_vagas = attrs.get('total_vagas', self.instance.total_vagas)
        total_apartamentos = attrs.get('total_apartamentos', self.instance.total_apartamentos)
        blocos = attrs.get('blocos', self.instance.blocos)

        # total_vagas não pode ser menor que garagens já cadastradas
        garagens_cadastradas = self.instance.garagens.count()
        if total_vagas is not None and total_vagas < garagens_cadastradas:
            raise serializers.ValidationError({
                'total_vagas': (
                    f'Não é possível reduzir para {total_vagas}. '
                    f'Já existem {garagens_cadastradas} garagem(ns) cadastrada(s).'
                )
            })

        # total_apartamentos não pode ser menor que titulares já cadastrados
        titulares_cadastrados = self.instance.usuarios.filter(tipo='morador', papel='titular').count()
        if total_apartamentos is not None and total_apartamentos < titulares_cadastrados:
            raise serializers.ValidationError({
                'total_apartamentos': (
                    f'Não é possível reduzir para {total_apartamentos}. '
                    f'Já existem {titulares_cadastrados} titular(es) cadastrado(s).'
                )
            })

        # blocos não pode ser menor que a quantidade de blocos distintos em uso
        blocos_em_uso = (
            self.instance.usuarios
            .filter(tipo='morador', bloco__isnull=False)
            .values_list('bloco', flat=True)
            .distinct()
            .count()
        )
        if blocos is not None and blocos < blocos_em_uso:
            raise serializers.ValidationError({
                'blocos': (
                    f'Não é possível reduzir para {blocos}. '
                    f'Já existem {blocos_em_uso} bloco(s) distintos em uso por moradores.'
                )
            })

        return attrs


class GaragemSerializer(serializers.ModelSerializer):
    disponivel = serializers.BooleanField(read_only=True)
    morador_nome = serializers.CharField(source='morador.nome', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    morador = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.filter(tipo='morador'),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Garagem
        fields = [
            'id', 'condominio', 'numero', 'tipo', 'tipo_display',
            'matricula', 'morador', 'morador_nome', 'disponivel',
        ]
        validators = []

    def validate(self, attrs):
        condominio = attrs.get('condominio', getattr(self.instance, 'condominio', None))
        tipo = attrs.get('tipo', getattr(self.instance, 'tipo', 'vinculada'))
        matricula = attrs.get('matricula', getattr(self.instance, 'matricula', None))

        # Condomínio não pode ser alterado no update
        if self.instance and 'condominio' in attrs and attrs['condominio'] != self.instance.condominio:
            raise serializers.ValidationError(
                {'condominio': 'O condomínio da garagem não pode ser alterado.'}
            )

        total_vagas = condominio.total_vagas or 0
        if total_vagas == 0:
            raise serializers.ValidationError(
                {'condominio': 'Este condomínio não possui vagas de garagem cadastradas.'}
            )

        # Limite de vagas (somente no cadastro)
        if not self.instance:
            vagas_existentes = Garagem.objects.filter(condominio=condominio).count()
            if vagas_existentes >= total_vagas:
                raise serializers.ValidationError(
                    {'numero': f'Limite atingido. O condomínio permite no máximo {total_vagas} vaga(s).'}
                )

        # Número único por condomínio
        numero = attrs.get('numero', getattr(self.instance, 'numero', None))
        duplicado_qs = Garagem.objects.filter(condominio=condominio, numero=numero)
        if self.instance:
            duplicado_qs = duplicado_qs.exclude(pk=self.instance.pk)
        if duplicado_qs.exists():
            raise serializers.ValidationError(
                {'numero': f'A garagem {numero} já está cadastrada neste condomínio.'}
            )

        # Vaga autônoma exige matrícula
        if tipo == 'autonoma' and not matricula:
            raise serializers.ValidationError(
                {'matricula': 'Matrícula é obrigatória para vagas autônomas (registro próprio no cartório).'}
            )

        # Matrícula única por condomínio (quando informada)
        if matricula:
            matricula_qs = Garagem.objects.filter(condominio=condominio, matricula=matricula)
            if self.instance:
                matricula_qs = matricula_qs.exclude(pk=self.instance.pk)
            if matricula_qs.exists():
                raise serializers.ValidationError(
                    {'matricula': f'Já existe uma vaga com a matrícula {matricula} neste condomínio.'}
                )

        # Validações do morador
        morador = attrs.get('morador', getattr(self.instance, 'morador', None) if 'morador' in attrs else None)
        if 'morador' in attrs and morador is not None:
            # Morador deve pertencer ao mesmo condomínio
            if morador.condominio_id != condominio.id:
                raise serializers.ValidationError(
                    {'morador': 'Este morador não pertence ao condomínio desta garagem.'}
                )
            # Somente titulares podem ter vaga atribuída
            if morador.papel != 'titular':
                raise serializers.ValidationError(
                    {'morador': 'Somente titulares podem ter vaga atribuída.'}
                )
            # Máximo de 2 vagas por morador
            vagas_do_morador = Garagem.objects.filter(morador=morador)
            if self.instance:
                vagas_do_morador = vagas_do_morador.exclude(pk=self.instance.pk)
            if vagas_do_morador.count() >= 2:
                raise serializers.ValidationError(
                    {'morador': 'Este morador já possui 2 vagas atribuídas (limite máximo).'}
                )

        return attrs


class UsuarioListSerializer(serializers.ModelSerializer):
    """Versão resumida para listagens"""
    condominio_nome = serializers.CharField(source='condominio.nome', read_only=True)
    garagens_numeros = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'nome', 'email', 'cpf', 'tipo', 'papel', 'apartamento', 'bloco',
            'garagens_numeros', 'condominio', 'condominio_nome', 'telefone', 'ativo',
        ]

    def get_garagens_numeros(self, obj):
        return list(obj.garagens.values_list('numero', flat=True))


class UsuarioSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    condominio_nome = serializers.CharField(source='condominio.nome', read_only=True)
    garagens = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email',
            'nome', 'cpf', 'condominio', 'condominio_nome', 'tipo', 'papel', 'telefone',
            'apartamento', 'bloco', 'garagens', 'foto', 'face_embeddings',
            'notificacoes_push', 'notificacoes_whatsapp', 'ativo',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['username', 'face_embeddings', 'created_at', 'updated_at']

    def get_garagens(self, obj):
        return [
            {'id': g.id, 'numero': g.numero, 'tipo': g.tipo, 'matricula': g.matricula}
            for g in obj.garagens.all()
        ]

    def validate_email(self, value):
        qs = Usuario.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Este e-mail já está cadastrado.')
        return value.lower()

    def validate(self, attrs):
        tipo = attrs.get('tipo', getattr(self.instance, 'tipo', None))
        papel = attrs.get('papel', getattr(self.instance, 'papel', 'titular'))
        condominio = attrs.get('condominio', getattr(self.instance, 'condominio', None))

        if tipo == 'sindico' and condominio:
            sindico_qs = Usuario.objects.filter(condominio=condominio, tipo='sindico')
            if self.instance:
                sindico_qs = sindico_qs.exclude(pk=self.instance.pk)
            if sindico_qs.exists():
                raise serializers.ValidationError({
                    'tipo': (
                        'Este condomínio já possui um síndico. '
                        'Um condomínio só pode ter um síndico responsável.'
                    )
                })

        if tipo == 'morador' and condominio:
            apartamento = attrs.get('apartamento', getattr(self.instance, 'apartamento', None))
            bloco = attrs.get('bloco', getattr(self.instance, 'bloco', None))

            if apartamento is None:
                raise serializers.ValidationError(
                    {'apartamento': 'Número do apartamento é obrigatório para moradores.'}
                )
            if apartamento < 1:
                raise serializers.ValidationError(
                    {'apartamento': 'Número do apartamento deve ser maior que zero.'}
                )

            if not bloco:
                raise serializers.ValidationError(
                    {'bloco': 'Identificação do bloco é obrigatória para moradores.'}
                )

            if papel == 'titular':
                # Limite de titulares pelo total de apartamentos
                total_apartamentos = condominio.total_apartamentos or 0
                if total_apartamentos > 0:
                    titulares_qs = Usuario.objects.filter(
                        condominio=condominio, tipo='morador', papel='titular'
                    )
                    if self.instance:
                        titulares_qs = titulares_qs.exclude(pk=self.instance.pk)
                    if titulares_qs.count() >= total_apartamentos:
                        raise serializers.ValidationError({
                            'apartamento': (
                                f'Limite atingido. O condomínio permite no máximo '
                                f'{total_apartamentos} titular(es).'
                            )
                        })

                # Apartamento + bloco únicos entre titulares
                duplicado_qs = Usuario.objects.filter(
                    condominio=condominio, tipo='morador', papel='titular',
                    apartamento=apartamento, bloco=bloco
                )
                if self.instance:
                    duplicado_qs = duplicado_qs.exclude(pk=self.instance.pk)
                if duplicado_qs.exists():
                    raise serializers.ValidationError({
                        'apartamento': (
                            f'Já existe um titular cadastrado no apartamento {apartamento} '
                            f'do bloco {bloco}.'
                        )
                    })

            elif papel == 'dependente':
                # Dependente exige titular no mesmo apartamento/bloco
                titular_existe = Usuario.objects.filter(
                    condominio=condominio, tipo='morador', papel='titular',
                    apartamento=apartamento, bloco=bloco
                ).exists()
                if not titular_existe:
                    raise serializers.ValidationError({
                        'papel': (
                            f'Não existe titular cadastrado no apartamento {apartamento} '
                            f'do bloco {bloco}. Cadastre o titular primeiro.'
                        )
                    })

        return attrs

    def create(self, validated_data):
        cpf_digits = ''.join(filter(str.isdigit, validated_data.get('cpf', '') or ''))
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
        instance.refresh_from_db()
        return instance


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    """Campos que o próprio usuário pode atualizar no seu perfil."""
    senha_atual = serializers.CharField(write_only=True, required=False)
    nova_senha = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Usuario
        fields = [
            'email', 'nome', 'telefone', 'foto',
            'notificacoes_push', 'notificacoes_whatsapp',
            'senha_atual', 'nova_senha',
        ]

    def validate(self, attrs):
        senha_atual = attrs.pop('senha_atual', None)
        nova_senha = attrs.pop('nova_senha', None)

        if nova_senha:
            if not senha_atual:
                raise serializers.ValidationError(
                    {'senha_atual': 'Informe a senha atual para definir uma nova senha.'}
                )
            if not self.instance.check_password(senha_atual):
                raise serializers.ValidationError(
                    {'senha_atual': 'Senha atual incorreta.'}
                )
            attrs['nova_senha'] = nova_senha

        return attrs

    def update(self, instance, validated_data):
        nova_senha = validated_data.pop('nova_senha', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if nova_senha:
            instance.set_password(nova_senha)
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
