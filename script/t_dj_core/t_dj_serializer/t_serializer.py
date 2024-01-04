import os.path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

import json

from django.core.serializers.json import Serializer as JsonSerializer
from django.core.serializers.python import Serializer as PythonSerializer
from django.core.serializers.pyyaml import Serializer as YamlSerializer
from users.models import CircleUsersModel
from fosun_circle.apps.common.tasks.task_zp_xgty import zp_xgty

users = CircleUsersModel.objects.filter(id__lt=10)
serializer = JsonSerializer()
# serializer = PythonSerializer()
# serializer = YamlSerializer()
ss = serializer.serialize(users, **{"indent": 4, "ensure_ascii": False})
print(ss)
# print(json.loads(ss)[0])

