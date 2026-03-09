from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CondominioViewSet, GaragemViewSet, UsuarioViewSet

router = DefaultRouter()
router.register('condominios', CondominioViewSet, basename='condominio')
router.register('garagens', GaragemViewSet, basename='garagem')
router.register('usuarios', UsuarioViewSet, basename='usuario')

urlpatterns = [
    path('', include(router.urls)),
]
