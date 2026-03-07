from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Usuario


class CpfEmailTokenSerializer(TokenObtainPairSerializer):
    """
    Login via CPF ou e-mail + senha.
    Substitui o campo 'username' padrão pelo campo 'login'.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('username', None)
        self.fields['login'] = serializers.CharField(label='CPF ou e-mail')

    def validate(self, attrs):
        login = attrs.get('login', '').strip()
        password = attrs.get('password', '')

        user = self._buscar_usuario(login)

        if user is None or not user.check_password(password):
            raise AuthenticationFailed('CPF/e-mail ou senha inválidos.')

        if not user.is_active:
            raise AuthenticationFailed('Usuário inativo. Entre em contato com o síndico.')

        refresh = self.get_token(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    def _buscar_usuario(self, login):
        cpf_digits = ''.join(filter(str.isdigit, login))

        # Busca por CPF — aceita com ou sem formatação (000.000.000-00 ou 00000000000)
        if len(cpf_digits) == 11:
            cpf_formatado = f'{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}'
            try:
                usuario = Usuario.objects.get(cpf__in=[cpf_digits, cpf_formatado])
                return usuario
            except Usuario.DoesNotExist:
                pass

        # Busca por e-mail
        try:
            return User.objects.get(email__iexact=login)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            pass

        return None


class CpfEmailTokenView(TokenObtainPairView):
    serializer_class = CpfEmailTokenSerializer