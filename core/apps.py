from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Enregistre les contrôles de configuration de production.
        # Ils ne sont PAS marqués `deploy=True` : ainsi un simple
        # `manage.py check` — celui que lance start.sh à chaque démarrage du
        # conteneur — les exécute et fait échouer le démarrage si la
        # configuration est dangereuse.
        from . import checks  # noqa: F401
