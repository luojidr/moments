from django.db import models

from fosun_circle.core.db.base import BaseAbstractModel


class AliStaticUploadModel(BaseAbstractModel):
    STATIC_CHOICES = [
        (1, "Image"),
        (2, "File"),
        (3, "Voice"),
    ]

    name = models.CharField('Name', max_length=200, default='', blank=True)
    url = models.CharField('URL', max_length=1000, default='', blank=True)
    key = models.CharField("key", unique=True, max_length=50, default="", blank=True)
    file_size = models.IntegerField("Size", default=0, blank=True)
    check_sum = models.CharField("MD5", max_length=64, default="", blank=True)
    is_share = models.BooleanField("Is Public", default=False, blank=True)
    is_success = models.BooleanField("Is Success", default=True, blank=True)
    access_token = models.CharField("Access Token", max_length=100, default="", blank=True)

    class Meta:
        db_table = 'circle_aliyun_static_upload'
        ordering = ['-id']
