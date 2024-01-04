import sys
import os.path
import logging
import django

logging.warning("Script Path: %s\n", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Config
print("Config.DJANGO_SETTINGS_MODULE:", Config.DJANGO_SETTINGS_MODULE)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", Config.DJANGO_SETTINGS_MODULE)
django.setup()

from fosun_circle.apps.users.models import BbsUserModel

# print(dir(BbsUserModel))
# print(BbsUserModel._meta.label)
# print(dir(BbsUserModel.Meta))
bbs_user = BbsUserModel.objects.get(id=1)
print(bbs_user)
