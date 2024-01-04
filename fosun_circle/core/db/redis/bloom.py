# -*- coding: utf-8 -*-

import sys

if sys.platform[:3].upper() == "WIN":
    from pybloom_live import BloomFilter
    PY_OS = "win"
else:
    """ pyreBloom.__init__(self, key, capacity, error, host='127.0.0.1', port=6379, password='', db=0) """
    from pyreBloom import pyreBloom as BloomFilter
    PY_OS = "linux"

from config.conf import RedisBloomConfig


class RedisBloomFilter(object):
    """ 基于redis的布隆过滤器
    Win 本地开发测试使用 https://github.com/jaybaird/python-bloomfilter，效率远不如 redis
    Linux https://github.com/seomoz/pyreBloom , pyreBloom 目前在PY3无法使用
    """

    def __init__(self, capacity=None, error_rate=0.001, name=None,
                 host=None, port=6379, password="", db=0):
        """
        pyreBloom will throw `TypeError: expected bytes, str found` when using Python3, but py2 is ok.
        :param capacity: int
        :param error_rate: float
        :param name: str, filter name
        :param host: str, redis host ip
        :param port: int, redis port
        :param password: str, redis password
        """
        if capacity is None:
            raise ValueError("布隆过滤器初始化容量不能为0")

        self.capacity = capacity
        self.error_rate = error_rate
        self.name = name or "RedisBloomFilter"

        self.host = host or self.config.get("host") or "127.0.0.1"
        self.port = port or self.config.get("port") or 6379
        self.db = db or self.config.get("db") or 0
        self.password = password or self.config.get("password") or ""

        init_kwargs = dict(capacity=self.capacity)

        if PY_OS == "win":
            init_kwargs.update(error_rate=self.error_rate)
        else:
            bytes_params = dict(name=self.name, host=self.host, password=self.password)
            for attr, value in bytes_params.items():
                if not isinstance(value, bytes):
                    bytes_val = bytes(value, encoding="utf-8")
                    setattr(self, attr, bytes_val)

            init_kwargs.update(
                key=self.name, error=self.error_rate,
                host=self.host, port=self.port, password=self.password, db=self.db
            )

        self._bloom = BloomFilter(**init_kwargs)

    def _setup(self):
        self.count = 0

    @property
    def config(self):
        if hasattr(self, "_blomm_config"):
            return self._blomm_config

        bloom_config = {}
        prefix = "REDIS_"

        for attr, value in RedisBloomConfig.__dict__.items():
            if attr.startswith(prefix):
                bloom_config[attr[len(prefix):]] = value

        self._blomm_config = bloom_config
        return self._blomm_config

    def __contains__(self, key):
        return key in self._bloom

    def contains(self, key):
        return self.__contains__(key)

    def add(self, key):
        """ Have Problem
        File "pyreBloom.pyx", line 70, in pyreBloom.pyreBloom.add (pyreBloom/pyreBloom.c:1478)
        File "pyreBloom.pyx", line 60, in pyreBloom.pyreBloom.put (pyreBloom/pyreBloom.c:1281)
        TypeError: expected bytes, int found
        :param key:
        :return:
        """
        # if self._bloom.count > self.capacity:
        #     raise IndexError("BloomFilter is at capacity")

        return self._bloom.add(key)

    def to_file(self):
        pass

    def from_file(self):
        pass



