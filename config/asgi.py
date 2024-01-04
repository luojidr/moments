"""
ASGI config for dj_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os
import logging

from django.core.asgi import get_asgi_application

from config.settings import Config

logging.warning("Asgi -> DEBUG:{0}，DJANGO_SETTINGS_MODULE:{1}".format(Config.DEBUG, Config.DJANGO_SETTINGS_MODULE))

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', Config.DJANGO_SETTINGS_MODULE)

application = get_asgi_application()
