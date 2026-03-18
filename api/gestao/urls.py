from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CondominioViewSet,
    GaragemViewSet,
    UsuarioViewSet,
    VisitanteViewSet,
    RegistroAcessoViewSet,
    dashboard_stats,
    validar_qr,
    vapid_public_key,
    push_subscribe,
)

router = DefaultRouter()
router.register('condominios', CondominioViewSet, basename='condominio')
router.register('garagens', GaragemViewSet, basename='garagem')
router.register('usuarios', UsuarioViewSet, basename='usuario')
router.register('visitantes', VisitanteViewSet, basename='visitante')
router.register('acessos', RegistroAcessoViewSet, basename='acesso')

urlpatterns = [
    # O endpoint validar-qr precisa vir ANTES do include do router para evitar
    # qualquer ambiguidade com a rota acessos/{pk}/.
    path('acessos/validar-qr/', validar_qr, name='validar-qr'),
    path('', include(router.urls)),
    path('dashboard/stats/', dashboard_stats, name='dashboard-stats'),
    path('push/vapid-key/', vapid_public_key, name='vapid-public-key'),
    path('push/subscribe/', push_subscribe, name='push-subscribe'),
]
