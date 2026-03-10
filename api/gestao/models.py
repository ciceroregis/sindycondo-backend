import uuid

from django.contrib.auth.models import AbstractUser, User
from django.db import models
from django.db.models.functions import Length

class Condominio(models.Model):
    nome = models.CharField(max_length=200)
    cnpj = models.CharField(max_length=200, unique=True, blank=True, null=True)
    endereco = models.TextField()
    cidade = models.CharField(max_length=200, blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    cep = models.CharField(max_length=20, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    blocos = models.IntegerField(blank=True, null=True, default=1)
    total_apartamentos = models.IntegerField(blank=True, null=True, default=1)
    total_vagas = models.IntegerField(blank=True, null=True, default=0)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "condominio"
        verbose_name = "Condominio"
        verbose_name_plural = "Condominios"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Usuario(User):
    TIPOS = [
        ('admin', 'Administrador'),
        ('sindico', 'Sindico'),
        ('porteiro', 'Porteiro'),
        ('morador', 'Morador'),
    ]

    PAPEIS = [
        ('titular', 'Titular'),
        ('dependente', 'Dependente'),
    ]

    nome = models.CharField(max_length=200)
    cpf = models.CharField(max_length=14, unique=True, blank=True, null=True)
    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, null=True, blank=True, related_name="usuarios")
    tipo = models.CharField(max_length=10, choices=TIPOS, default="morador")
    papel = models.CharField(max_length=10, choices=PAPEIS, default='titular', blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    apartamento = models.IntegerField(blank=True, null=True)
    bloco = models.CharField(max_length=20, blank=True, null=True)
    foto = models.ImageField(upload_to='uploads/', blank=True, null=True)
    face_embeddings = models.JSONField(null=True, blank=True)
    notificacoes_push = models.BooleanField(default=True)
    notificacoes_whatsapp = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "usuarios"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=['condominio'],
                condition=models.Q(tipo='sindico'),
                name='unique_sindico_por_condominio',
            )
        ]

    def __str__(self):
        return f'{self.get_full_name()} ({self.tipo}) - {self.condominio}'

class Garagem(models.Model):
    TIPOS = [
        ('autonoma', 'Autônoma'),
        ('vinculada', 'Vinculada'),
        ('comum', 'Comum'),
    ]

    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name='garagens')
    numero = models.CharField(max_length=20)
    tipo = models.CharField(max_length=10, choices=TIPOS, default='vinculada')
    matricula = models.CharField(max_length=50, blank=True, null=True)
    morador = models.ForeignKey(
        'Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='garagens'
    )

    class Meta:
        db_table = 'garagens'
        verbose_name = 'Garagem'
        verbose_name_plural = 'Garagens'
        ordering = ['condominio', Length('numero'), 'numero']
        unique_together = [('condominio', 'numero')]

    def __str__(self):
        ocupante = f'→ {self.morador.nome}' if self.morador_id else 'disponível'
        return f'Garagem {self.numero} [{self.get_tipo_display()}] ({self.condominio}) — {ocupante}'

    @property
    def disponivel(self):
        return self.morador_id is None


class Visitante(models.Model):
    STATUS = [
        ('pending', 'Aguardando aprovação'),
        ('approved', 'Aprovado'),
        ('blocked', 'Bloqueado'),
        ('expired', 'Expirado'),
    ]

    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name='visitantes')
    morador = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True,
                                related_name='visitantes_autorizados')
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=20, blank=True)  # armazenado criptografado
    telefone = models.CharField(max_length=20, blank=True)
    foto = models.ImageField(upload_to='visitantes/', null=True, blank=True)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    max_pessoas = models.IntegerField(default=1)
    qr_code_id = models.UUIDField(default=uuid.uuid4, unique=True)
    qr_code_imagem = models.ImageField(upload_to='qrcodes/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    observacoes = models.TextField(blank=True)
    usos_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "visitantes"
        verbose_name = 'Visitante'
        verbose_name_plural = 'Visitantes'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.nome} → {self.morador}'


class RegistroAcesso(models.Model):
    TIPOS = [
        ('qr', 'QR Code'),
        ('facial', 'Reconhecimento Facial'),
        ('placa', 'Placa Veículo'),
        ('manual', 'Liberação Manual'),
        ('chave', 'Chave Digital'),
    ]

    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name='acessos')
    visitante = models.ForeignKey(Visitante, on_delete=models.SET_NULL, null=True, blank=True)
    morador = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='acessos')
    porteiro = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='acessos_liberados')
    tipo_acesso = models.CharField(max_length=20, choices=TIPOS)
    autorizado = models.BooleanField(default=False)
    motivo_negado = models.CharField(max_length=200, blank=True)
    face_confidence = models.FloatField(null=True, blank=True)
    placa_detectada = models.CharField(max_length=20, blank=True)
    imagem_snapshot = models.ImageField(upload_to='acessos/', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "registros_acesso"
        verbose_name = 'Registro de Acesso'
        verbose_name_plural = 'Registros de Acesso'
        ordering = ['-timestamp']

    def __str__(self):
        status = '✅' if self.autorizado else '❌'
        return f'{status} {self.tipo_acesso} - {self.timestamp.strftime("%d/%m %H:%M")}'


class AuditLog(models.Model):
    """LGPD - Log de auditoria para todas as ações sensíveis"""
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    acao = models.CharField(max_length=100)
    tabela = models.CharField(max_length=50)
    registro_id = models.IntegerField(null=True)
    detalhes = models.JSONField(null=True)
    ip_address = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "log_audit"
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'
        ordering = ['-timestamp']