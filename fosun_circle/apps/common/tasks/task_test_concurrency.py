import time

from config.celery import celery_app
from fosun_circle.libs.log import task_logger as logger


@celery_app.task
def test_concurrency_limit(to_backend='redis', **kwargs):
    """
    @celery_app.task(ignore_result=True)
    def test_concurrency_limit(to_backend='django-cache', **kwargs):
        pass

    django-cache: Celery的 CELERY_CACHE_BACKEND 配置，需要在 settings.CACHES 中配置
    """
    logger.info("test_concurrency_limit")
    time.sleep(.2)

