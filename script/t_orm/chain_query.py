import json
import os.path
import traceback

import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from users.models import CircleUsersModel
from ding_talk.models import DingAppMediaModel


if __name__ == "__main__":
    queryset = DingAppMediaModel.objects.filter(is_del=False).values()
    print(queryset)

    for obj in queryset:
        print(obj)
