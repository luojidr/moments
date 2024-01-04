import time

from config.celery import celery_app
from fosun_circle.libs.log import task_logger as logger


@celery_app.task
def test_backend_default(**kwargs):
    return 'django-db'  # default local db


@celery_app.task
def test_backend_prod_db(to_backend='djx_db', **kwargs):
    return 'prod_db'


@celery_app.task
def test_backend_local_redis(to_backend='redis', **kwargs):
    return 'local_redis'


@celery_app.task
def test_backend_prod_redis(to_backend='djx_cache', **kwargs):
    return 'prod_redis'


# @celery_app.task
def test_backend_prod_cache_redis(to_backend='djy-cache', **kwargs):
    return 'prod_redis-djy'


@celery_app.task
def test_backend_local_file(to_backend='file', **kwargs):
    return 'local_file'

