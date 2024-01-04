import os.path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from django.contrib.sessions.backends.cache import SessionStore
# from django.contrib.sessions.backends.db import SessionStore

ss = SessionStore("sessionid32524323")
# print(ss.__dict__)
print(ss.cache_key)
# print(ss._session)

ss["name"] = "ding"
print(ss.cache_key)

# ss["name2"] = "ding2"
# print(ss.cache_key)
