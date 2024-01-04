import os
import string
import time
import random
import traceback

from Crypto.Cipher import AES
from django.conf import settings

from fosun_circle.libs.utils.crypto import AESCipher
from fosun_circle.libs.log import task_logger as logger

__all__ = ["TokenHelper"]


class TokenHelper:
    SEQUENCE = string.ascii_letters + string.digits

    def __init__(self, ticket=None, app_scope=None):
        self._ticket = ticket
        self._app_scope = app_scope

    @property
    def api_ticket(self):
        return self._ticket or os.environ.get("API_TICKET")

    @property
    def app_scope(self):
        return self._app_scope or settings.APP_NAME

    def _get_random(self, k=6):
        return "".join([random.choice(self.SEQUENCE) for _ in range(6)])

    @property
    def token(self):
        token_key = os.environ.get("IHCM_API_TOKEN")
        if not token_key:
            raise ValueError("IHCM_API_TOKEN is empty!")

        token = cipher_text = None
        aes = AESCipher(key=token_key, mode=AES.MODE_CBC)

        try:
            raw_text = "{ticket}:{app_scope}:{timestamp}:{random_key}".format(
                ticket=self.api_ticket, app_scope=self.app_scope,
                timestamp=int(time.time()), random_key=self._get_random(),
            )
            token = cipher_text = aes.encrypt(raw=raw_text)
        except Exception as e:
            logger.error("get once token error: %s", e)
            logger.error(traceback.format_exc())

        if not cipher_text:
            raise ValueError("Encrypted message error")

        return token

    def get_token(self):
        return dict(name=self.app_scope, token=self.token)
