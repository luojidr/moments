# Base Configuration Control
# If you want to get different environment variables, need to variable acquisition
# So Custom Config class can do that

import os
import logging
import platform

import environ
from django.conf import ENVIRONMENT_VARIABLE

__all__ = ["Config"]

python_version = tuple([int(v) for v in platform.python_version_tuple()])

# if python_version < (3, 8, 6):
if python_version < (3, 7, 9):
    raise EnvironmentError("Python Version less than `3.8.6`")

env = environ.Env()
APP_ENV = env.str("APP_ENV", "DEV")

if APP_ENV == "DEV":
    from config.settings import dev as ConfigBase
else:
    from config.settings import prod as ConfigBase

logging.warning("Project go into [{0}] environ!......".format(APP_ENV))


class Config(object):
    """ 所有已 `get_` 前缀的变量都会自动加入类中 """

    CONFIG_PREFIX = "get_to_"

    DEBUG = ConfigBase.DEBUG
    APP_ENV = APP_ENV
    ROOT_DIR = ConfigBase.ROOT_DIR

    @classmethod
    def setup(cls):
        """ 将配置加载到 django.conf.settings 中 """
        from django.conf import settings

        cls.configuration()
        os.environ.setdefault(ENVIRONMENT_VARIABLE, getattr(cls, ENVIRONMENT_VARIABLE))

        for name in dir(cls):
            if name.startswith("_") or not name.isupper():
                continue

            if name not in settings.__dict__:
                settings.__setattr__(name, getattr(Config, name))

    @classmethod
    def configuration(cls):
        assert_msg = "{2}环境 APP_ENV:{0}与 DEBUG:{1}配置错误"
        if cls.APP_ENV == "DEV" and not cls.DEBUG:
            raise AssertionError(assert_msg.format(cls.APP_ENV, cls.DEBUG, "测试"))

        if cls.APP_ENV == "PROD" and cls.DEBUG:
            raise AssertionError(assert_msg.format(cls.APP_ENV, cls.DEBUG, "生产"))

        method_name_list = [attr for attr in dir(cls) if attr.startswith(cls.CONFIG_PREFIX)]

        for method_name in method_name_list:
            cls_attr_name = method_name.lstrip(cls.CONFIG_PREFIX).upper()

            if not hasattr(Config, cls_attr_name):
                unbound_method = getattr(cls, method_name, None)

                if unbound_method is None:
                    continue

                setattr(Config, cls_attr_name, unbound_method(Config()))

    def get_to_django_settings_module(self):
        """ 获取项目配置文件路径 """
        assert self.APP_ENV in ["DEV", "PROD"], "APP_ENV 不存在"

        if self.APP_ENV == "DEV":
            settings_module_path = "config.settings.dev"
        else:
            settings_module_path = "config.settings.prod"

        logging.warning("Project DJANGO_SETTINGS_MODULE: `{0}` ! ......".format(settings_module_path))
        return settings_module_path


Config.setup()

