import time
import os.path
import os.path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from django.conf import settings
from django.core.files import locks

STATE_DIR_PATH = os.path.join(settings.MEDIA_ROOT, "file_state")


def my_lock(i):
    filename = os.path.join(STATE_DIR_PATH, "tmp.txt")

    with open(filename, 'wb') as fp:
        locks.lock(fp, locks.LOCK_EX)
        fp.write(b'Django' + str(i).encode('u8'))
        time.sleep(10)


