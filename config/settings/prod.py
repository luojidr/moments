from .base import *  # noqa
from .base import env

from dotenv import load_dotenv, find_dotenv

DEPLOY = os.environ.get('DEPLOY')
IS_OVERSEAS_REGION = os.getenv('APP_REGION') == 'OVERSEAS_EUR'

if DEPLOY == 'DOCKER':
    if IS_OVERSEAS_REGION:
        config_filename = '.prod_k8s_overseas_env'
    else:
        config_filename = '.prod_k8s_env'

    ENV_PATH = os.path.join(SETTINGS_DIR, config_filename)
else:
    ENV_PATH = os.path.join(SETTINGS_DIR, '.prod_env')
    # raise ValueError('Circle PRD Settings Error!')

logging.warning('获取的环境配置<prod.py>: %s', ENV_PATH)
load_dotenv(find_dotenv(ENV_PATH, raise_error_if_not_found=True))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="wj*u^fjsr-x)nm^d&&f%^6x2*vt10ll$m515&zs@tt+8eb2syk"
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])


# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv("PG:PROD:CIRCLE:DB_NAME"),
        'HOST': os.getenv("PG:PROD:CIRCLE:HOST"),
        'PORT': os.getenv("PG:PROD:CIRCLE:PORT"),
        'USER': os.getenv("PG:PROD:CIRCLE:USER"),
        'PASSWORD': os.getenv("PG:PROD:CIRCLE:PASSWORD"),
        "POOL_OPTIONS": {
            "POOL_SIZE": 20,
            "MAX_OVERFLOW": 20
        }
    },

    'default_slave': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv("PG:PROD:CIRCLE:DB_NAME"),
        'HOST': os.getenv("PG:PROD:CIRCLE:HOST"),
        'PORT': os.getenv("PG:PROD:CIRCLE:PORT"),
        'USER': os.getenv("PG:PROD:CIRCLE:USER"),
        'PASSWORD': os.getenv("PG:PROD:CIRCLE:PASSWORD"),
        "POOL_OPTIONS": {
            "POOL_SIZE": 20,
            "MAX_OVERFLOW": 20
        }
    },

    'bbs_user': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv("PG:PROD:BBS:DB_NAME"),
        'HOST': os.getenv("PG:PROD:BBS:HOST"),
        'PORT': os.getenv("PG:PROD:BBS:PORT"),
        'USER': os.getenv("PG:PROD:BBS:USER"),
        'PASSWORD': os.getenv("PG:PROD:BBS:PASSWORD"),
        "POOL_OPTIONS": {
            "POOL_SIZE": 20,
            "MAX_OVERFLOW": 20
        }
    },

    'migrate_dest': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'fosun_circle',
        'HOST': 'pgm-.pg.rds.aliyuncs.com',
        'PORT': '5432',
        'USER': 'fosun_circle',
        'PASSWORD': 'IX3YkvU8XNpi',
    },
}

logging.warning('Prod DATABASES: %s', DATABASES)

# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{user}:{password}@{host}:{port}/{db}".format(
            user=os.getenv("REDIS:USER"), password=os.getenv("REDIS:PASSWORD"),
            host=os.getenv("REDIS:HOST"), port=os.getenv("REDIS:PORT"), db=os.getenv("REDIS:DB0"),
        ),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100, "decode_responses": True},
            "PASSWORD": os.getenv("REDIS:PASSWORD"),

            # # Mimicing memcache behavior.
            # # http://jazzband.github.io/django-redis/latest/#_memcached_exceptions_behavior
            # "IGNORE_EXCEPTIONS": True,
        },
    },

    "redis_db1": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{user}:{password}@{host}:{port}/1".format(
            user=os.getenv("REDIS:USER"), password=os.getenv("REDIS:PASSWORD"),
            host=os.getenv("REDIS:HOST"), port=os.getenv("REDIS:PORT")
        ),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100, "decode_responses": True},
            "PASSWORD": os.getenv("REDIS:PASSWORD"),
        },
    },

    "django-cache": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{user}:{password}@{host}:{port}/{db}".format(
            user=os.getenv("REDIS:USER"), password=os.getenv("REDIS:PASSWORD"),
            host=os.getenv("REDIS:HOST"), port=os.getenv("REDIS:PORT"), db=os.getenv("REDIS:DB0"),
        ),
        "KEY_PREFIX": "celery_results",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100, "decode_responses": True},
            "PASSWORD": os.getenv("REDIS:PASSWORD"),
        },
    },
}
logging.warning('Prod CACHES: %s', CACHES)

# SESSION
# ------------------------------------------------------------------------------
# session 默认存储数据库，利用缓存减少sql请求
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'


# # SECURITY
# # ------------------------------------------------------------------------------
# # https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# # https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
# SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# # https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
# SESSION_COOKIE_SECURE = True
# # https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
# CSRF_COOKIE_SECURE = True
# # https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# # https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# # TODO: set this to 60 seconds first and then to 518400 once you prove the former works
# SECURE_HSTS_SECONDS = 60
# # https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
# SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
#     "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
# )
# # https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
# SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# # https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
# SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
#     "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", default=True
# )


# STATIC
# ------------------------
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
# WHITENOISE_MAX_AGE = 30 * 24 * 60 * 60
COMPRESS_ENABLED = env.bool('COMPRESS_ENABLED')  # 开启压缩


# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates

# TEMPLATES[-1]["OPTIONS"]["loaders"] = [
#     # type: ignore[index] # noqa F405
#     (
#         "django.template.loaders.cached.Loader",
#         [
#             "django.template.loaders.filesystem.Loader",
#             "django.template.loaders.app_directories.Loader",
#         ],
#     )
# ]


# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email

# DEFAULT_FROM_EMAIL = env(
#     "DJANGO_DEFAULT_FROM_EMAIL", default="ihouse_sync <noreply@example.com>"
# )
#
# # https://docs.djangoproject.com/en/dev/ref/settings/#server-email
# SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
#
# # https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
# EMAIL_SUBJECT_PREFIX = env(
#     "DJANGO_EMAIL_SUBJECT_PREFIX", default="[ihouse_sync]"
# )


# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.

# ADMIN_URL = env("DJANGO_ADMIN_URL")


# Anymail
# ------------------------------------------------------------------------------
# https://anymail.readthedocs.io/en/stable/installation/#installing-anymail

# INSTALLED_APPS += ["anymail"]  # noqa F405
# # https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
# # https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
# # https://anymail.readthedocs.io/en/stable/esps
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# ANYMAIL = {}


# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.


# Dingtalk UUC（Deprecated）
# ------------------------------------------------------------------------------
UUC_URL = ""


# Sentry
# ------------------------------------------------------------------------------

if SENTRY_SDK_INSTALLED:
    SENTRY_DSN = env("SENTRY_DSN")
    SENTRY_LOG_LEVEL = env.int("DJANGO_SENTRY_LOG_LEVEL", logging.INFO)

    if SENTRY_SDK_INSTALLED:
        sentry_logging = LoggingIntegration(
            level=SENTRY_LOG_LEVEL,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR,  # Send errors as events
        )

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[sentry_logging, DjangoIntegration(), CeleryIntegration()],
        )

CIRCLE_HOST = 'https://circle.fosun.com'
CIRCLE_API_HOST = 'https://api-circle.fosun.com'
FRONT_HOST = 'https://ui-circle.fosun.com'

MENU_ROOT_ID = 1
