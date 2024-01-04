"""
WSGI config for dj_backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os
import logging

from django.conf import settings
from django.core.wsgi import get_wsgi_application

from config.settings import Config

from whitenoise import WhiteNoise

args = (Config.DEBUG, Config.DJANGO_SETTINGS_MODULE, settings.IS_DOCKER)
logging.warning("Wsgi -> DEBUG:%s, DJANGO_SETTINGS_MODULE:%s, IS_DOCKER: %s", *args)

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', Config.DJANGO_SETTINGS_MODULE)

application = get_wsgi_application()
application = WhiteNoise(application, root="staticfiles/")  # Use whitenoise application
