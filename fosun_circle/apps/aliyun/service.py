import os.path
import uuid

import cv2
from django.conf import settings

from fosun_circle.libs.utils.snow_flake import Snowflake
from fosun_circle.core.ali_oss.upload import AliOssFileUploader
from fosun_circle.constants.enums.oss_type import AliOssTypeEnum
from fosun_circle.libs.utils.crypto import BaseCipher
from fosun_circle.libs.log import dj_logger as logger


class AliOssUploadService(object):
    MAX_VIDEO_SIZE = 400 << 20  # 最大 10Mb
    MAX_VIDEO_DURATION = 10 * 60  # 最长 10m

    TMP_UPLOAD_PATH = "%s/" % settings.BASE_MEDIA_PATH

    def __init__(self, callback=None):
        self._callback = callback
        self._uid = str(Snowflake().get_id())

    def get_video_duration_and_style(self, tmp_filename):
        duration = -1
        screen_style = None  # landscape:横屏   vertical:竖屏
        cap = cv2.VideoCapture(tmp_filename)

        if cap.isOpened():
            rate = cap.get(5)           # 帧速率
            frame_num = cap.get(7)      # 视频文件中的帧数
            duration = frame_num / rate

            width = cap.get(3)          # 在视频流的帧的宽度
            height = cap.get(4)         # 在视频流的帧的高度

            screen_style = "landscape" if width >= height else "vertical"

            cap.release()
            return round(duration, 2), screen_style

        return duration, screen_style

    def _save_tmp_file(self, tmp_upload_fd):
        _, ext = os.path.splitext(tmp_upload_fd.name)
        tmp_filename = self.TMP_UPLOAD_PATH + str(uuid.uuid1()).replace("-", "") + ext

        if not os.path.exists(self.TMP_UPLOAD_PATH):
            os.makedirs(self.TMP_UPLOAD_PATH)

        with open(tmp_filename, "wb") as fp:
            # 保存到临时文件中
            for chunk_bytes in tmp_upload_fd.chunks(chunk_size=1 << 20):
                fp.write(chunk_bytes)

        return tmp_filename

    def _check_temporary_video(self, tmp_filename):
        # 计算视频时长与宽窄屏样式
        duration, screen_style = self.get_video_duration_and_style(tmp_filename)

        if duration == -1:
            os.remove(tmp_filename)
            raise ValueError("视频时长解析失败")
        elif duration > self.MAX_VIDEO_DURATION:
            os.remove(tmp_filename)
            raise ValueError("视频时长(%ss)已经超过 %ss" % (duration, self.MAX_VIDEO_DURATION))

        # 视频重命名
        filename, ext = os.path.splitext(tmp_filename)
        new_tmp_filename = filename + "_" + screen_style + ext
        os.rename(tmp_filename, new_tmp_filename)

        return new_tmp_filename

    def _get_check_sum(self, filepath):
        with open(filepath, "rb") as fp:
            return BaseCipher.crypt_md5(fp.read())

    def upload(self, tmp_upload_name=None, tmp_upload_fd=None, **kwargs):
        assert tmp_upload_name or tmp_upload_fd

        if tmp_upload_fd:
            tmp_upload_name = self._save_tmp_file(tmp_upload_fd)

        _, ext = os.path.splitext(tmp_upload_name)
        file_size = os.path.getsize(tmp_upload_name)
        check_sum = self._get_check_sum(tmp_upload_name)
        video_types = AliOssFileUploader.UPLOAD_FILE_TYPE[AliOssTypeEnum.VIDEO.type]

        if ext in video_types:
            if file_size > self.MAX_VIDEO_SIZE:
                raise ValueError("视频大小已经超过 %sMb" % (self.MAX_VIDEO_SIZE >> 20))

            tmp_filename = self._check_temporary_video(tmp_upload_name)
        else:
            tmp_filename = tmp_upload_name

        uploader = AliOssFileUploader(callback=self._callback, cb_kwargs=dict(uid=self._uid))
        result = uploader.complete_upload(filename=tmp_filename, data=None, is_async=True, **kwargs)
        logger.info('AliOssUploadService.upload => result: %s', result)

        return dict(
            result, key=self._uid,
            file_size=file_size, check_sum=check_sum
        )
