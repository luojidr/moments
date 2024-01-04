from django.conf import settings
from django.utils import timezone


def now(offset=None):
    n = timezone.now()

    if not offset and settings.IS_DOCKER:
        offset = 8
    else:
        offset = offset if offset else 0

    return n + timezone.timedelta(hours=offset)

