import pymysql
import psycopg2

from werobot.config import Config
from werobot.robot import _DEFAULT_CONFIG
from werobot.session.mysqlstorage import MySQLStorage
from werobot.session.postgresqlstorage import PostgreSQLStorage
from werobot.session.redisstorage import RedisStorage

from django.db import connection
from django.conf import settings
from django_redis import get_redis_connection


def get_session_storage():
    try:
        redis_conn = get_redis_connection()
        return RedisStorage(redis=redis_conn)
    except NotImplementedError:
        pass

    vendor = connection.vendor
    default_params = settings.DATABASES["default"]
    db_params = {
        "user": default_params["USER"],
        "password": default_params["PASSWORD"],
        "host": default_params["HOST"],
        "port": default_params["PORT"],
        "database": default_params["NAME"],
    }

    if vendor == "mysql":
        storage = MySQLStorage(conn=pymysql.connect(**db_params))
    elif vendor == "postgresql":
        storage = PostgreSQLStorage(conn=psycopg2.connect(**db_params))
    else:
        raise NotImplementedError("vendor error")

    return storage


class WeRobotConfig:
    TOKEN = "werobot20220817"
    APP_ID = "wx344a8d6f132f4165"
    APP_SECRET = "79e182239495f28e65d7e3959bd8c54e"
    SESSION_STORAGE = get_session_storage()
    # SESSION_STORAGE = None
    # SERVER = "gevent"
    # HOST = "0.0.0.0"
    # PORT = "8888"
    # ENCODING_AES_KEY = None

    MENU_ITEMS = {
        "button": [
            {
                "type": "click",
                "name": "今日歌曲",
                "key": "V1001_TODAY_MUSIC"
            },

            {
                "type": "click",
                "name": "歌手简介",
                "key": "V1001_TODAY_SINGER"
            },

            {
                "name": "菜单",
                "sub_button": [
                    {
                        "type": "view",
                        "name": "搜索",
                        "url": "http://www.soso.com/"
                    },

                    {
                        "type": "view",
                        "name": "视频",
                        "url": "http://v.qq.com/"
                    },

                    {
                        "type": "click",
                        "name": "赞一下我们",
                        "key": "V1001_GOOD"
                    }
                ]
            },
        ]
    }

    @classmethod
    def get_config(cls):
        config = Config()
        default_config_keys = _DEFAULT_CONFIG.keys()

        for key in dir(cls):
            if key in default_config_keys:
                config[key] = getattr(cls, key)

        return config
