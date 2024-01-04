import json
import os.path
import traceback

import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from users.models import CircleUsersModel


def query_raw():
    sql = "SELECT * FROM circle_users WHERE id <= 1650"
    queryset = CircleUsersModel.objects.raw(sql)
    count = len(queryset)
    print(count, queryset)
    for obj in queryset:
        print(obj)


if __name__ == "__main__":
    query_raw()
