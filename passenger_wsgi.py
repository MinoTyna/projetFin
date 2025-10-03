import sys
import os

# Ajouter le chemin vers ton projet Django
sys.path.insert(0, '/home/aufsarl1/ventesproduit')

# Indiquer o첫 sont les settings Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'monbackend.settings'

# Activer l'application WSGI de Django
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
