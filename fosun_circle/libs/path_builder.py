import os.path
import random
import string
import logging

from bson import ObjectId
from django.conf import settings
from django.utils.deconstruct import deconstructible

logger = logging.getLogger('django')


@deconstructible
class PathBuilder:
    BUCKET_SIZE = 256
    BUCKET_PATH = "ding_media"
    PER_BUCKET_SIZE = 2000

    def __init__(self, field_name, **kwargs):
        self._field_name = field_name
        self._kwargs = kwargs
        self._bucket_max_size = self.BUCKET_SIZE * self.PER_BUCKET_SIZE

    def __call__(self, media_instance, filename):
        media_root = settings.MEDIA_ROOT
        # media_root = '/data/bms/'
        media_path = "".join([random.choice("0123456789abcdef") for _ in range(2)])

        ok_count = 0
        abs_media_path = None
        try_times = self.BUCKET_SIZE

        # 文件后缀
        src_fn, ext = os.path.splitext(filename)

        while ok_count < try_times:
            # K8S MAS服务暂不知指定目录下的子目录的读写权限
            if settings.IS_DOCKER:
                abs_media_path = media_root
            else:
                abs_media_path = os.path.join(media_root, self.BUCKET_PATH, media_path)

            logger.info("PathBuilder => abs_media_path: %s", abs_media_path)

            if not os.path.exists(abs_media_path):
                os.makedirs(abs_media_path)

            filename_list = [
                fn for fn in os.listdir(abs_media_path)
                if os.path.isfile(os.path.join(abs_media_path, fn))
            ]

            try:
                if len(filename_list) > self.PER_BUCKET_SIZE:
                    logger.warning("[%s] 目录下已到达存储个数: %s", abs_media_path, self.PER_BUCKET_SIZE)

                # 保证重命名后的文件名的唯一性
                post_name = "".join(random.choices(string.ascii_letters, k=8)) + "_" + str(ObjectId())
                media_instance.post_filename = post_filename = post_name + ext

                media_name = media_instance.key + ext
                media_url = os.path.join(settings.MEDIA_URL, media_name).replace("\\", "/")
                media_instance.media_url = media_url if media_url.startswith("/") else "/" + media_url

                # The start position cannot be '/' with media path's to django 3.1.14
                # raise SuspiciousFileOperation(
                # django.core.exceptions.SuspiciousFileOperation:
                # Detected path traversal attempt in '/tmp/media/ding_media\8e\IpxcdlQw_630c7c192209b5c5d.jpg'
                full_media_path = os.path.join(abs_media_path, post_filename)      # 保存文件的实际路径
                logger.info("PathBuilder => full_media_path: %s", full_media_path)
                media_instance.media = full_media_path[1:] if full_media_path.startswith("/") else full_media_path

                return full_media_path[len(media_root):]
            except FileExistsError:
                ok_count += 1

        if abs_media_path is None:
            raise FileExistsError("Bucket: %s 已达到最大存储上限: %s" % (abs_media_path, self._bucket_max_size))




