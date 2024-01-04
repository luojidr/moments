# -*- coding: utf-8 -*-
""" `pycryptodome` Python Package"""

import hashlib
from binascii import b2a_hex, a2b_hex

from Crypto.Cipher import AES


class BaseCipher(object):
    @staticmethod
    def crypt_md5(s, salt=None):
        if not isinstance(salt, (type(None), str)):
            raise ValueError("Md5加盐值类型错误!")

        s += salt or ""
        m = hashlib.md5()
        m.update(s)
        return m.hexdigest()


class AESCipher(object):
    def __init__(self, key):
        if not isinstance(key, bytes):
            key = key.encode("utf-8")

        self.key = key
        self.mode = AES.MODE_CBC

    def encrypt(self, raw):
        # 密钥key长度必须为16（AES-128）、24（AES-192）、32（AES-256）Bytes长度.目前AES-128足够用
        crypto = AES.new(self.key, self.mode, self.key)

        if not isinstance(raw, bytes):
            raw = raw.encode("utf-8")

        if len(raw) % 16 != 0:
            addition = 16 - len(raw) % 16
        else:
            addition = 0

        text = raw + (b'\0' * addition)
        cipher_text = crypto.encrypt(text)

        # AES加密后的字符串不一定是ascii字符集，统一把加密后的字符串转化为16进制字符串
        return b2a_hex(cipher_text).decode("utf-8")

    def decrypt(self, text):
        if not isinstance(text, bytes):
            text = text.encode("utf-8")

        crypto = AES.new(self.key, self.mode, self.key)
        plain_text = crypto.decrypt(a2b_hex(text))

        return plain_text.rstrip(b'\0').decode("utf-8")
