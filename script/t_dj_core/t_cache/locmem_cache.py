import json
import time
import zlib
import os.path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from django.core.cache import cache, caches
from django.core.cache.backends.locmem import LocMemCache

locmen_cache = caches["locmem"]

