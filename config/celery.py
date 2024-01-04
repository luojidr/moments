import os
from config.settings import Config

# Set DJANGO_SETTINGS_MODULE is important
os.environ.setdefault('DJANGO_SETTINGS_MODULE', Config.DJANGO_SETTINGS_MODULE)

from fosun_circle.core.djcelery_helper.djcelery import app as celery_app

__all__ = ["celery_app"]
