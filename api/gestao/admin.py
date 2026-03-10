from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditLog, Condominio, Garagem, RegistroAcesso, Usuario, Visitante


@admin.register(Condominio)
class CondominioAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cnpj', 'cidade', 'estado', 'blocos', 'total_apartamentos', 'total_vagas', 'ativo']
    list_filter = ['ativo', 'estado', 'cidade']
    search_fields = ['nome', 'cnpj', 'endereco']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['nome']


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ['nome', 'email', 'cpf', 'tipo', 'papel', 'condominio', 'apartamento', 'bloco', 'ativo', 'is_active']
    list_filter = ['tipo', 'papel', 'ativo', 'is_active', 'condominio']
    search_fields = ['nome', 'email', 'cpf', 'username']
    ordering = ['nome']
    readonly_fields = ['created_at', 'updated_at', 'last_login', 'date_joined']

    fieldsets = (
        ('Identificação', {'fields': ('username', 'password')}),
        ('Dados Pessoais', {'fields': ('nome', 'email', 'cpf', 'telefone', 'foto')}),
        ('Condomínio', {'fields': ('condominio', 'tipo', 'papel', 'apartamento', 'bloco')}),
        ('Preferências', {'fields': ('notificacoes_push', 'notificacoes_whatsapp')}),
        ('Status', {'fields': ('ativo', 'is_active', 'is_staff', 'is_superuser')}),
        ('Permissões', {'fields': ('groups', 'user_permissions')}),
        ('Datas', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        ('Identificação', {'fields': ('username', 'password1', 'password2')}),
        ('Dados Pessoais', {'fields': ('nome', 'email', 'cpf', 'telefone')}),
        ('Condomínio', {'fields': ('condominio', 'tipo', 'papel', 'apartamento', 'bloco')}),
    )


@admin.register(Garagem)
class GaragemAdmin(admin.ModelAdmin):
    list_display = ['numero', 'tipo', 'matricula', 'condominio', 'morador', 'disponivel']
    list_filter = ['tipo', 'condominio']
    search_fields = ['numero', 'matricula', 'morador__nome', 'condominio__nome']
    ordering = ['condominio', 'numero']


@admin.register(Visitante)
class VisitanteAdmin(admin.ModelAdmin):
    list_display = ['nome', 'condominio', 'morador', 'status', 'data_inicio', 'data_fim', 'usos_count']
    list_filter = ['status', 'condominio']
    search_fields = ['nome', 'cpf', 'morador__nome']
    readonly_fields = ['qr_code_id', 'qr_code_imagem', 'usos_count', 'created_at']
    ordering = ['-created_at']


@admin.register(RegistroAcesso)
class RegistroAcessoAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'condominio', 'tipo_acesso', 'autorizado', 'morador', 'visitante', 'porteiro']
    list_filter = ['autorizado', 'tipo_acesso', 'condominio']
    search_fields = ['morador__nome', 'visitante__nome', 'placa_detectada']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'usuario', 'acao', 'tabela', 'registro_id', 'ip_address']
    list_filter = ['acao', 'tabela']
    search_fields = ['usuario__nome', 'acao', 'tabela', 'ip_address']
    readonly_fields = ['timestamp', 'usuario', 'acao', 'tabela', 'registro_id', 'detalhes', 'ip_address']
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
