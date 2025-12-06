import os
from django.core.wsgi import get_wsgi_application

try:
    import certifi
    os.environ["SSL_CERT_FILE"] = certifi.where()
except ImportError:
    pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recipify.settings')

application = get_wsgi_application()
