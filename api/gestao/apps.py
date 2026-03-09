from django.apps import AppConfig


class GestaoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.gestao"

    def ready(self):
        import api.gestao.signals  # noqa: F401
