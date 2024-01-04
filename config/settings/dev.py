import logging

from .base import *  # noqa
from .base import env

import os
from datetime import timedelta
from dotenv import load_dotenv, find_dotenv

DEPLOY = os.environ.get('DEPLOY')
IS_OVERSEAS_REGION = os.getenv('APP_REGION') == 'OVERSEAS_EUR'

if DEPLOY == 'DOCKER':
    if IS_OVERSEAS_REGION:
        config_filename = '.uat_k8s_overseas_env'
    else:
        config_filename = '.uat_k8s_env'

    ENV_PATH = os.path.join(SETTINGS_DIR, config_filename)
else:
    ENV_PATH = os.path.join(SETTINGS_DIR, '.local_env')

logging.warning('获取的环境配置<dev.py> DEPLOY[%s]: %s', DEPLOY, ENV_PATH)
load_dotenv(find_dotenv(ENV_PATH, raise_error_if_not_found=True))

# INSTALLED_APPS
# ------------------------------------------------------------------------------
# Development whitenoise
INSTALLED_APPS.insert(INSTALLED_APPS.index('django.contrib.staticfiles'), 'whitenoise.runserver_nostatic')
COMPRESS_ENABLED = env.bool('COMPRESS_ENABLED')

# Profile Silk Package
# ------------------------------------------------------------------------------
# https://github.com/jazzband/django-silk
ACTIVE_SILK = False

# Database
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

if os.environ.get('DEPLOY') == 'DOCKER':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': os.getenv("PG:DEV:CIRCLE:DB_NAME"),
            'HOST': os.getenv("PG:DEV:CIRCLE:HOST"),
            'PORT': os.getenv("PG:DEV:CIRCLE:PORT"),
            'USER': os.getenv("PG:DEV:CIRCLE:USER"),
            'PASSWORD': os.getenv("PG:DEV:CIRCLE:PASSWORD"),
        },

        'default_slave': {
            # 'ENGINE': 'django.db.backends.mysql',
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': os.getenv("PG:DEV:CIRCLE:DB_NAME"),
            'HOST': os.getenv("PG:DEV:CIRCLE:HOST"),
            'PORT': os.getenv("PG:DEV:CIRCLE:PORT"),
            'USER': os.getenv("PG:DEV:CIRCLE:USER"),
            'PASSWORD': os.getenv("PG:DEV:CIRCLE:PASSWORD"),
        }
    }

else:
    DATABASES = {
        'default': {
            # 'ENGINE': 'django.db.backends.mysql',
            # 'ENGINE': 'fosun_circle.contrib.db_pool.backends.mysql',
            # 'NAME': os.getenv("MYSQL:DEV:DB_NAME"),
            # 'HOST': os.getenv("MYSQL:DEV:HOST"),      # 192.168.190.128 | Root!1234
            # 'PORT': os.getenv("MYSQL:DEV:PORT"),
            # 'USER': os.getenv("MYSQL:DEV:USER"),
            # 'PASSWORD': os.getenv("MYSQL:DEV:PASSWORD"),
            # 'OPTIONS': {'charset': 'utf8mb4'},

            'ENGINE': 'fosun_circle.contrib.db_pool.backends.postgresql',
            'NAME': os.getenv("PG:DEV:CIRCLE:DB_NAME"),
            'HOST': os.getenv("PG:DEV:CIRCLE:HOST"),
            'PORT': os.getenv("PG:DEV:CIRCLE:PORT"),
            'USER': os.getenv("PG:DEV:CIRCLE:USER"),
            'PASSWORD': os.getenv("PG:DEV:CIRCLE:PASSWORD"),
        },

        'default_slave': {
            'ENGINE': 'fosun_circle.contrib.db_pool.backends.postgresql',
            'NAME': os.getenv("PG:DEV:CIRCLE:DB_NAME"),
            'HOST': os.getenv("PG:DEV:CIRCLE:HOST"),
            'PORT': os.getenv("PG:DEV:CIRCLE:PORT"),
            'USER': os.getenv("PG:DEV:CIRCLE:USER"),
            'PASSWORD': os.getenv("PG:DEV:CIRCLE:PASSWORD"),
        },

        # UAT
        # 'migrate_dest': {
        #     'ENGINE': 'django.db.backends.postgresql_psycopg2',
        #     'NAME': 'fosun_circle_bbs',
        #     'HOST': 'pgm-.pg.rds.aliyuncs.com',
        #     'PORT': '5432',
        #     'USER': 'fosun_circle_bbs',
        #     'PASSWORD': '',
        # },

        # PRD RDS
        'migrate_dest': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'fosun_circle',
            'HOST': 'pgm-.pg.rds.aliyuncs.com',
            'PORT': '5432',
            'USER': 'fosun_circle',
            'PASSWORD': '',
        },
    }

DATABASES.update({
    'bbs_user': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv("PG:DEV:BBS:DB_NAME"),
        'HOST': os.getenv("PG:DEV:BBS:HOST"),
        'PORT': os.getenv("PG:DEV:BBS:PORT"),
        'USER': os.getenv("PG:DEV:BBS:USER"),
        'PASSWORD': os.getenv("PG:DEV:BBS:PASSWORD"),
        "POOL_OPTIONS": {
            "POOL_SIZE": 20,
            "MAX_OVERFLOW": 20
        }
    },

    'circle': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv("PG:DEV:CIRCLE:DB_NAME"),
        'HOST': os.getenv("PG:DEV:CIRCLE:HOST"),
        'PORT': os.getenv("PG:DEV:CIRCLE:PORT"),
        'USER': os.getenv("PG:DEV:CIRCLE:USER"),
        'PASSWORD': os.getenv("PG:DEV:CIRCLE:PASSWORD"),
        "POOL_OPTIONS": {
            "POOL_SIZE": 20,
            "MAX_OVERFLOW": 20
        }
    },
})

logging.warning('Dev DATABASES: %s', DATABASES)


# APPS
# ------------------------------------------------------------------------------
# Application definition
if ACTIVE_SILK:
    INSTALLED_APPS.append("silk")
    MIDDLEWARE.append("silk.middleware.SilkyMiddleware")
    DATABASE_APPS_ROUTER_MAPPING.update({
        "silk": "default",
    })

    # 使用Python的内置cProfile分析器
    SILKY_PYTHON_PROFILER = True

    # 生成.prof文件，silk产生的程序跟踪记录，详细记录来执行来哪个文件，哪一行，用了多少时间等信息
    SILKY_PYTHON_PROFILER_BINARY = True

    # .prof文件保存路径
    SILKY_PYTHON_PROFILER_RESULT_PATH = '%s/silk/profiles/' % BASE_MEDIA_PATH

# INSTALLED_APPS.append('easypush')

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="n20IAqHopdmar3ipc31YXe9fhoJ1NSM9N1PoEYZbAEuX8cZpGJxttaiJwm3jvcUZ",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["*"]


# MIDDLEWARE
# ------------------------------------------------------------------------------
# Application Middleware


# LOGGING
# ------------------------------------------------------------------------------
LOGGING['loggers']['django']['handlers'].append("console")
LOGGING['loggers']['celery.task']['handlers'].append("console")
LOGGING['loggers']['celery.worker']['handlers'].append("console")
LOGGING['loggers']['celery.beat']['handlers'].append("console")


# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches

# CACHES = {
#     "default": {
#         "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
#         "LOCATION": "",
#     }
# }

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{user}:{password}@{host}:{port}/{db}".format(
            user=os.getenv("REDIS:USER"), password=os.getenv("REDIS:PASSWORD"),
            host=os.getenv("REDIS:HOST"), port=os.getenv("REDIS:PORT"), db=os.getenv("REDIS:DB0"),
        ),
        "KEY_PREFIX": "circle",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # "PARSER_CLASS": 'redis.connection.HiredisParser',  # Hiredis is WAY faster than redis-py
            # redis-py>=2.10.6, decode_responses: False, else True
            #   maybe raise UnicodeDecodeError: 'utf-8' codec can't decode byte 0x80 in position 0: invalid start byte
            "CONNECTION_POOL_KWARGS": {"max_connections": 100, "decode_responses": False},
            "PASSWORD": None,
        }
    },

    "redis_db1": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{user}:{password}@{host}:{port}/1".format(
            user=os.getenv("REDIS:USER"), password=os.getenv("REDIS:PASSWORD"),
            host=os.getenv("REDIS:HOST"), port=os.getenv("REDIS:PORT")
        ),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100, "decode_responses": False},
            "PASSWORD": None,
        }
    },

    "django-cache": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{user}:{password}@{host}:{port}/{db}".format(
            user=os.getenv("REDIS:USER"), password=os.getenv("REDIS:PASSWORD"),
            host=os.getenv("REDIS:HOST"), port=os.getenv("REDIS:PORT"), db=os.getenv("REDIS:DB0"),
        ),
        "KEY_PREFIX": "circle",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100, "decode_responses": False},
            "PASSWORD": None,
        }
    },

    "djy-cache": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{user}:{password}@{host}:{port}/{db}".format(
            user=os.getenv("REDIS:DEV:USER"), password=os.getenv("REDIS:DEV:PASSWORD"),
            host=os.getenv("REDIS:DEV:HOST"), port=os.getenv("REDIS:DEV:PORT"), db=os.getenv("REDIS:DEV:DB0"),
        ),
        "KEY_PREFIX": "djx",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100, "decode_responses": False},
            "PASSWORD": None,
        }
    },

    "locmem": {
        "BACKEND": 'django.core.cache.backends.locmem.LocMemCache',
    },

    # this cache backend will be used by django-debug-panel
    'debug-panel': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/var/tmp/debug-panel-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 200
        }
    }
}
logging.warning('Dev CACHES: %s', CACHES)

# Rest Framework Swagger
# ------------------------------------------------------------------------------
SWAGGER_SETTINGS = {
    "JSON_EDITOR": True,
}


# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
LOGGING["loggers"].update({
    "django.db.backends": {
        "level": "DEBUG",
        "handlers": ["console"],
        "propagate": False,
    },
})


# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)


# WhiteNoise
# ------------------------------------------------------------------------------
# http://whitenoise.evans.io/en/latest/django.html#using-whitenoise-in-development
# WhiteNoise effect `django-debug-toolbar` static files
# INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS  # noqa F405

# Django-Compressor
# ------------------------------------------------------------------------------
if os.environ.get('APP_LOCAL') == 'LOCAL':
    COMPRESS_ENABLED = False  # IS_DOCKER: False, Only local development

# django-debug-toolbar
# ------------------------------------------------------------------------------
# https://django-debug-toolbar.readthedocs.io/en/latest/
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
# https://marcgibbons.com/django-rest-swagger/#installation

# pympler: https://django-debug-toolbar.readthedocs.io/en/stable/panels.html#pympler
# debug_panel: 未更新，Django3.x版本不支持
# INSTALLED_APPS += ["debug_toolbar", 'pympler']  # noqa F405
# INSTALLED_APPS += ["debug_toolbar", 'pympler', 'debug_panel']  # noqa F405

# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
# MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa F405

# https://github.com/recamshak/django-debug-panel
# Replace  the Django Debug Toolbar middleware with the Django Debug Panel one. Replace:
# MIDDLEWARE += ['debug_panel.middleware.DebugPanelMiddleware']  # noqa F405
# https://django-debug-toolbar.readthedocs.io/en/stable/panels.html#default-built-in-panels
DEBUG_TOOLBAR_PANELS = [
    # "debug_toolbar.panels.history.HistoryPanel",
    "debug_toolbar.panels.versions.VersionsPanel",
    "debug_toolbar.panels.timer.TimerPanel",
    "debug_toolbar.panels.settings.SettingsPanel",
    "debug_toolbar.panels.headers.HeadersPanel",
    "debug_toolbar.panels.request.RequestPanel",
    "debug_toolbar.panels.sql.SQLPanel",
    "debug_toolbar.panels.staticfiles.StaticFilesPanel",
    "debug_toolbar.panels.templates.TemplatesPanel",
    "debug_toolbar.panels.cache.CachePanel",
    "debug_toolbar.panels.signals.SignalsPanel",
    "debug_toolbar.panels.logging.LoggingPanel",
    "debug_toolbar.panels.redirects.RedirectsPanel",
    "debug_toolbar.panels.profiling.ProfilingPanel",

    "pympler.panels.MemoryPanel",
]
# https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
DEBUG_TOOLBAR_CONFIG = {
    # "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
    'INTERCEPT_REDIRECTS': False,
    "SHOW_TEMPLATE_CONTEXT": True,
    'HIDE_DJANGO_SQL': False,
    # 'JQUERY_URL': "http://code.jquery.com/jquery-2.1.1.min.js",
    'JQUERY_URL': "https://cdn.bootcss.com/jquery/2.2.4/jquery.min.js",
}
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
INTERNAL_IPS = ["*"]
ACTIVE_DEBUG_TOOLBAR = False


# Django Rest Swagger
# ------------------------------------------------------------------------------
# https://django-rest-swagger.readthedocs.io/en/latest/#django-rest-swagger

REST_FRAMEWORK.update(
    {
        "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema"
    }
)

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += [
    "rest_framework_swagger",
]  # noqa F405
# Celery
# ------------------------------------------------------------------------------
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-always-eager
# CELERY_TASK_ALWAYS_EAGER = True
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-eager-propagates
# CELERY_TASK_EAGER_PROPAGATES = True
# Your stuff...
# ------------------------------------------------------------------------------


# Dingtalk UUC
# ------------------------------------------------------------------------------
UUC_URL = ""


# Sentry Config
# ------------------------------------------------------------------------------

SENTRY_DSN = "https://bfd2a34e4eb24b2895f9450343ff8073@o395930.ingest.sentry.io/5248606"
SENTRY_LOG_LEVEL = env.int("DJANGO_SENTRY_LOG_LEVEL", logging.INFO)

if SENTRY_SDK_INSTALLED:
    sentry_logging = LoggingIntegration(
        level=SENTRY_LOG_LEVEL,  # Capture info and above as breadcrumbs
        event_level=logging.INFO,  # Send errors as events
    )

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[sentry_logging, DjangoIntegration(), CeleryIntegration()],
    )

JWT_AUTH = {
    "JWT_PASSWORD_FIELD": "sms_code",
    "JWT_AUTH_COOKIE": "Auth-Jwt",
    "JWT_AUTH_HEADER_PREFIX": "Auth-Jwt",
    "JWT_EXPIRATION_DELTA": datetime.timedelta(hours=24),
    "JWT_REFRESH_EXPIRATION_DELTA": datetime.timedelta(hours=24),
}


# EASYPUSH
EASYPUSH = {
    "default": {
        "BACKEND": os.getenv("EASYPUSH:BACKEND"),
        "CORP_ID": os.getenv("EASYPUSH:CORP_ID"),
        "AGENT_ID": os.getenv("EASYPUSH:AGENT_ID"),
        "APP_KEY": os.getenv("EASYPUSH:APP_KEY"),
        "APP_SECRET": os.getenv("EASYPUSH:APP_SECRET"),
    },
}


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_code',
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('XX-Token',),
}

HEALTH_CHECK = {
    'DISK_USAGE_MAX': 90,  # percent
    'MEMORY_MIN': 100,    # in MB
}

BBS_SECRET_KEY = "$3)=dh3_kdd$nq4t#5j2)2p(eb66s+chi5y95-ft2e4+-8#sl7"
CIRCLE_HOST = 'https://circle.uat.fosun.com'
CIRCLE_API_HOST = 'https://api-circle.uat.fosun.com'
FRONT_HOST = 'https://ui-circle.uat.fosun.com'


if DEPLOY != 'DOCKER':
    CIRCLE_HOST = 'http://127.0.0.1:8000'

MENU_ROOT_ID = 1
