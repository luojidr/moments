import json
import warnings
import datetime
from typing import Tuple, List, Mapping, Set, FrozenSet
from typing import (
    Awaitable,
    Optional,
    Union,
)

from redis import __version__, VERSION
from redis.exceptions import DataError, ExecAbortError
from django_redis import get_redis_connection


def _encode(value):
    """Return a bytestring or bytes-like representation of the value"""
    if isinstance(value, (bytes, memoryview)):
        return value
    elif isinstance(value, bool):
        # special case bool since it is a subclass of int
        return int(value)
    elif isinstance(value, (int, float)):
        value = repr(value).encode()
    elif value is None:
        value = ''
    elif isinstance(value, datetime.timedelta):
        pass
    elif isinstance(value, datetime.datetime):
        value = value.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(value, datetime.date):
        value = value.strftime('%Y-%m-%d')
    elif isinstance(value, (Tuple, List, Set)):
        value = json.dumps(value)
    elif isinstance(value, FrozenSet):
        raise TypeError('Object of type frozenset is not JSON serializable')

    if not isinstance(value, (str, bytes)):
        # a value we don't know how to deal with. throw an error
        typename = type(value).__name__
        raise DataError(
            f"Invalid input of type: '{typename}'. "
            f"Convert to a bytes, string, int or float first."
        )

    if isinstance(value, str):
        value = value.encode('utf-8', 'strict')
    return value


def get_hashmap_mapping(mapping=None, items=None):
    if not mapping and not items:
        raise DataError("'mapping' or 'items' with no key/value pairs")

    mapping = dict(items or [], **(mapping or {}))
    return {_encode(key): _encode(value) for key, value in mapping.items()}


def hset(
        name: str,
        key: Optional[str] = None,
        value: Optional[str] = None,
        mapping: Optional[dict] = None,
        items: Optional[list] = None,
        expires: Union[Union[datetime.timedelta, int], None] = None,
        alias: Optional[str] = "default"
) -> Union[Awaitable[int], int]:
    """
    Set ``key`` to ``value`` within hash ``name``,
    ``mapping`` accepts a dict of key/value pairs that will be
    added to hash ``name``.
    ``items`` accepts a list of key/value pairs that will be
    added to hash ``name``.

    Returns 1 if HSETNX created a field, otherwise 0 if redis < (3, 5, 0).
    Returns the number of fields that were added.
    """
    ret = None
    conn = get_redis_connection(alias=alias)
    mapping = mapping or {}

    if key and value:
        mapping[key] = value

    if items:
        mapping.update(dict(items))

    mapping = get_hashmap_mapping(mapping)

    if VERSION <= (3, 4, 1):
        # Only keywords: key, value
        if mapping or items:
            warnings.warn("redis-py(version: %s) unexpected keyword argument 'mapping' and 'items'" % __version__)

        ret = conn.hmset(name, mapping=mapping)

    if VERSION >= (3, 5, 0):
        if VERSION <= (4, 1, 4):
            # Only keywords: key, value, mapping
            if items:
                warnings.warn("redis-py(version: %s) unexpected keyword argument 'items'" % __version__)

        if VERSION >= (4, 2, 0):
            # Have keywords: key, value, mapping, items
            pass

        ret = conn.hset(name, mapping=mapping)

    if ret is None:
        raise ExecAbortError("redis-py(%s) is unexpected version" % __version__)

    if isinstance(expires, datetime.timedelta):
        expires = int(expires.total_seconds())

    conn.expire(name, expires)
    return ret
