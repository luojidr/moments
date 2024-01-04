import json
import time
import zlib
import os.path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from django.core import signing
from django.core.signing import Signer, TimestampSigner


def low_level_signer():
    signer = Signer()
    value = signer.sign("dingxt@fosun.com")  # dingxt@fosun.com:LjBqTcT6aWwwnaaelgikkWRmI8uKq4-di7ZI5Q7PPqo
    value1 = signer.signature("dingxt@fosun.com")
    print(value)
    print(value1)
    raw = signer.unsign(value)
    # raw1 = signer.unsign(value1)  # BadSignature: django.core.signing.BadSignature: No ":" found in value
    print("raw:", raw)

    signer_ts = TimestampSigner()
    ts_value = signer_ts.sign("hello")
    print("ts_value:", ts_value)

    time.sleep(3)
    signer_ts.unsign(ts_value, max_age=2)  # SignatureExpired: django.core.signing.SignatureExpired: Signature age 3.3407630920410156 > 2 seconds


def normal_signer():
    """ 签名加密比较简单，很容易破解 """
    obj = dict(name="dingxt", age=34, email='dingxt@fosun.com' * 1000)
    value = signing.dumps(obj=obj)
    print("value           :", len(value), value)

    value_compressed = signing.dumps(obj=obj, compress=True)
    print("value_compressed:", len(value_compressed), value_compressed)
    print(signing.loads(value_compressed))

    # 压缩大小比较
    # raw = dict(name="124235436457567" * 1000)
    # s_dump = signing.JSONSerializer().dumps(raw)
    # print("s_dump:", len(s_dump), s_dump)
    # data = signing.b64_encode(s_dump).decode()
    # print("data:", len(data), type(data), data)

    # compressed_0 = str(zlib.compress(s_dump, 0))
    # print("compressed_0:", len(compressed_0), type(compressed_0), compressed_0)
    #
    # compressed_1 = zlib.compress(s_dump, 1)
    # print("compressed_1:", len(compressed_1), type(compressed_1), "%s" % compressed_1)
    #
    # compressed_2 = zlib.compress(s_dump, 2)
    # print("compressed_2:", len(compressed_2), type(compressed_2), "%s" % compressed_2)


if __name__ == "__main__":
    normal_signer()

