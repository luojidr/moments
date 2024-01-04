import os.path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

import time
from django.core.cache import cache
import lzma
import lz4.frame
import lz4.block
import zlib

value = "Python安装lz4-0.10.1遇到的坑_Python_脚本之家" * 1000
print("value size:", len(value))

start_time = time.time()

# lzma 压缩后的大小最小，但是耗费时间也最长
lzma_compressed = lzma.compress(value.encode())
print("lzma_compressed:", lzma_compressed)
print("lzma_compressed size:", len(lzma_compressed))  # 264

start1_time = time.time()
print("lzma_compressed cost:", start1_time - start_time)  # 0.019162654876708984

# lz4 压缩后的大小最大，但是耗费时间也最短
lz4_compressed = lz4.frame.compress(value.encode())
print("\nlz4_compressed:", lz4_compressed)
print("lz4_compressed size:", len(lz4_compressed))  # 2494

start2_time = time.time()
print("lz4_compressed cost:", start2_time - start1_time)  # 0.00422978401184082


def zlib_compress(level):
    # zlib 压缩后的大小介于 lzma 与 lz4 之间，耗费时间也比较适宜

    start3_time = time.time()
    zlib_compressed = zlib.compress(value.encode(),  level)
    # print("zlib_compressed:",  zlib_compressed)
    print("zlib_compressed size:", len(zlib_compressed))  # 1661
    print("zlib_compressed cost:", time.time() - start3_time)  # 0.00951075553894043
    print()


if __name__ == "__main__":
    time.sleep(2)
    for level in [-1] + list(range(10)):
        print("----------- level: %s -----------" % level)
        print(level)
        zlib_compress(level)
