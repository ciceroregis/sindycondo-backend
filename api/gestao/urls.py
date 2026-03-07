from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CondominioViewSet, UsuarioViewSet

router = DefaultRouter()
router.register('condominios', CondominioViewSet, basename='condominio')
router.register('usuarios', UsuarioViewSet, basename='usuario')

urlpatterns = [
    path('', include(router.urls)),
]
