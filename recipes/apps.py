from django.apps import AppConfig

class RecipesConfig(AppConfig):
    """Django app config for recipes; loads signal handlers on ready."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recipes'

    def ready(self):
        """Import signal modules to register handlers."""
        import recipes.social_signals
        import recipes.signals
