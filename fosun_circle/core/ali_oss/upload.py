import uuid
import time
import os.path
import traceback
import urllib.parse
import threading
try:
    from collections import Iterable
except ImportError:
    from collections.abc import Iterable

import cv2
import oss2
from oss2.models import PartInfo
from oss2 import SizedFileAdapter, determine_part_size

from django.conf import settings

from .base import AliOssBase
from .detector import AliScanDetector

from fosun_circle.libs.decorators import to_retry
from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.constants.enums.oss_type import AliOssTypeEnum


class AliOssFileUploader(AliOssBase):
    """ OSS 文件上传 """
    PART_SIZE = 10 << 20
    MAX_BUCKET_SIZE = 63
    TMP_STORAGE_PATH = "%s/" % settings.BASE_MEDIA_PATH

    MAX_VIDEO_SIZE = 400 << 20  # 最大 400Mb
    MAX_VIDEO_DURATION = 10 * 60  # 最长 10m

    ON_ANTI_SPAM_CHECK = False  # 默认关闭反垃圾审查

    UPLOAD_FILE_TYPE = {
        AliOssTypeEnum.IMAGE.type: (".jpg", ".jpeg", ".png", ".svg"),
        AliOssTypeEnum.FILE.type: (".txt", ".doc", ".docx"),
        AliOssTypeEnum.VIDEO.type: (".mp4", ".avi", ".wmv", ".mpg", ".mpeg", ".mov", ".rm", ".ram"),
        AliOssTypeEnum.VOICE.type: (".mp3", ".cda", ".wav", ".aif", ".aiff", ".mid", ".wma", ".ra", ".vqf", ".ape"),
    }

    def __init__(self, bucket_name=None, endpoint=None, **kwargs):
        """
        :param bucket_name: string, 文件存储的位置
        :param endpoint:    string,
        :param kwargs:      dict, key 或 secret
        """
        self._cb_args = kwargs.pop("cb_args", ())
        self._cb_kwargs = kwargs.pop("cb_kwargs", {})
        self._callback = kwargs.pop("callback", lambda *args, **kw: 0)

        super(AliOssFileUploader, self).__init__(**kwargs)

        self._bucket_name = bucket_name or self.conf.BUCKET_NAME
        self._endpoint = endpoint or self.conf.ENDPOINT

        connect_timeout = kwargs.pop("timeout", 5 * 60)
        self._scan_detector = AliScanDetector()
        self._auth = oss2.Auth(self._access_key_id, self._access_key_secret)
        self._bucket = oss2.Bucket(self._auth, self._endpoint, self._bucket_name, connect_timeout=connect_timeout)

    def _check_anti_scan(self, filename=None, file_like=None):
        """ 文本、图片、视频等文件的反垃圾审查校验

        :return bytes: 反垃圾审查校验后的字节串
        """
        if filename is None:
            raise ValueError("文件名错误")

        if not os.path.exists(filename) and file_like is None:
            raise ValueError("文件(%s)不存在" % filename)

        if len(self._bucket_name) > self.MAX_BUCKET_SIZE:
            raise ValueError("Bucket Name 超过最大长度(max length:63)")

        file_type = self._get_file_type(filename)
        data = self._get_object_data(filename, file_like)
        detect_method = self._get_check_method(file_type=file_type)

        logger.info('AliOssFileUploader._check_anti_scan => detect_method: %s, file_type: %s', detect_method, file_type)

        detect_method(content=data)
        return data

    def _get_file_type(self, filename):
        file_type = None
        _, ext = os.path.splitext(filename.lower())

        for f_type, suffix_list in self.UPLOAD_FILE_TYPE.items():
            if ext in suffix_list:
                file_type = f_type
                break

        assert file_type in self.UPLOAD_FILE_TYPE, "文件上传类型错误！"
        return file_type

    def _get_check_method(self, file_type):
        """ 获取反垃圾审核方法 """
        method_name = "detect_" + AliOssTypeEnum.get_name(oss_type=file_type)
        detect_method = getattr(self._scan_detector, method_name)
        return detect_method

    def get_bucket_key(self, file_type=0):
        if file_type == AliOssTypeEnum.IMAGE.type:
            bucket_key = self.conf.IMAGE_BUCKET_KEY
        elif file_type == AliOssTypeEnum.VIDEO.type:
            bucket_key = self.conf.VIDEO_BUCKET_KEY
        else:
            bucket_key = ""
            self.logger.error("未找到 BUCKET_KEY 配置")

        return bucket_key

    def _progress_callback(self, bytes_consumed, total_bytes):
        """ 进度回调函数。可以用来实现进度条等功能 """

    def _get_object_data(self, filename, data=None):
        # 文件内容
        if data and isinstance(data, (str, bytes, type(u""))):
            # 字符串, Bytes, Unicode字符
            return data
        elif isinstance(data, Iterable):
            # 网络流
            return data
        elif data is None:
            # 本地文件
            with open(filename, "rb") as fp:
                data = fp.read()

            return data

        raise ValueError("上传阿里云的文件内容错误")

    def _get_oss_key(self, filename):
        filename = os.path.basename(filename.lower())
        file_type = self._get_file_type(filename)

        new_list = filename.split("_")
        new_list.insert(-1, str(int(time.time())))
        new_filename = "_".join(new_list)
        oss_key = "%s/%s" % (self.get_bucket_key(file_type=file_type), new_filename)

        return oss_key

    def _get_oss_url(self, oss_key):
        result = urllib.parse.urlparse(self._endpoint)
        scheme = result.scheme
        hostname = result.hostname

        if oss_key.startswith("/"):
            oss_key = oss_key[1:]

        oss_url_fmt = "{scheme}://{bucket_name}.{hostname}/{oss_key}"
        oss_kwargs = dict(scheme=scheme, hostname=hostname, oss_key=oss_key, bucket_name=self._bucket_name)

        return oss_url_fmt.format(**oss_kwargs)

    def callback_after_upload(self, filename, key, is_check=True, callback=None, cb_args=(), cb_kwargs=None):
        error = ""
        cb_args = cb_args or self._cb_args
        cb_kwargs = cb_kwargs or self._cb_kwargs
        callback = callback or self._callback

        try:
            self._put_object(filename, key, is_check=is_check)
        except Exception as e:
            error = str(e)
            self.logger.error('==>>> AliOssFileUploader error: %s', error)
            self.logger.error(traceback.format_exc())
        finally:
            os.remove(filename)  # 删除临时文件
            self.logger.info("AliOssFileUploader Callback cb_args:%s, cb_kwargs:%s", cb_args, cb_kwargs)

            if self._callback:
                try:
                    cb_kwargs.update(error=error)
                    callback(*cb_args, **cb_kwargs)
                except Exception as e:
                    self.logger.error("AliOssFileUploader Callback err:%s", e)
                    self.logger.error(traceback.format_exc())

    @to_retry
    def complete_upload(self, filename, data=None, is_async=False, is_check=True, **kwargs):
        """ 简单上传(可异步)
        便捷的用于上传本地文件: bucket.put_object_from_file

        :param filename: str, 文件路径, eg: /tmp/upload/mmexport1655179692406.mp4
        :param data: 待上传的内容。
        :type data: bytes，str或file-like object
        :param is_async: bool, 是否异步
        :param is_check bool, 反垃圾审查

        :return: class:`PutObjectResult <oss2.models.PutObjectResult>`
        """
        key = self._get_oss_key(filename)
        oss_url = self._get_oss_url(oss_key=key)
        self.logger.info("put_object oss_url: %s", oss_url)

        if self._get_file_type(filename) == AliOssTypeEnum.VIDEO.type:
            video_img_url = self.get_video_frame_image(filename)
        else:
            video_img_url = ""

        if not is_async:
            self._put_object(filename, key, data=data, is_check=is_check)
            os.remove(filename)  # 删除临时文件
        else:
            t_args = (filename, key)
            t_kwargs = dict(is_check=is_check)

            t = threading.Thread(target=self.callback_after_upload, args=t_args, kwargs=t_kwargs)
            t.setDaemon(True)
            t.start()

        return dict(url=oss_url, img_url=video_img_url)

    def _put_object(self, filename, key, data=None, is_check=True):
        """ 小文件可以简单上传，大文件必须分片上传(未实现) """
        headers = dict()
        start_time = time.time()

        # 反垃圾审查
        if is_check:
            scan_data = self._check_anti_scan(filename, file_like=data)
        else:
            scan_data = self._get_object_data(filename)

        result = self._bucket.put_object(
            key=key, data=scan_data, headers=headers,
            progress_callback=self._progress_callback,
        )

        status_code = result.status  # HTTP返回码
        request_id = result.request_id  # 请求ID。请求ID是本次请求的唯一标识，强烈建议在程序日志中添加此参数
        etag = result.etag  # ETag是put_object方法返回值特有的属性，用于标识一个Object的内容
        resp_headers = result.headers  # HTTP响应头部

        log_args = (status_code, request_id, etag, resp_headers)
        self.logger.info("AliOssFileUpload._put_object => status:%s, request_id:%s,etag:%s, resp_headers:%s", *log_args)
        self.logger.info("AliOssFileUpload._put_object ok, cost time:%s", time.time() - start_time)

        return result

    def get_object_meta(self, key, params=None, headers=None):
        meta_result = self._bucket.get_object_meta(key, params=params, headers=headers)
        self.logger.info(meta_result)
        return meta_result

    def get_object(self,
                   key,
                   byte_range=None,
                   headers=None,
                   progress_callback=None,
                   process=None,
                   params=None):
        result_stream = self._bucket.get_object(key, byte_range, headers, progress_callback, process, params)
        self.logger.info(result_stream)
        return result_stream

    def _put_multipart_object(self, filename, key, is_scan=True):
        """ 分片上传 """
        parts = []
        headers = dict()
        start_time = time.time()

        # 反垃圾审查
        if is_scan:
            self._check_anti_scan(filename)

        total_size = os.path.getsize(filename)
        part_size = determine_part_size(total_size, preferred_size=self.PART_SIZE)  # 确定分片大小
        upload_id = self._bucket.init_multipart_upload(key).upload_id

        with open(filename, 'rb') as fd:
            part_number = 1
            offset = 0

            while offset < total_size:
                num_to_upload = min(part_size, total_size - offset)

                # 调用SizedFileAdapter(fd, size)方法会生成一个新的文件对象，重新计算起始追加位置。
                part_result = self._bucket.upload_part(
                    key=key, upload_id=upload_id,
                    part_number=part_number, data=SizedFileAdapter(fd, num_to_upload)
                )
                parts.append(PartInfo(part_number, part_result.etag))

                offset += num_to_upload
                part_number += 1

        result = self._bucket.complete_multipart_upload(key, upload_id, parts, headers=headers)

        self.logger.info("AliOssFileUpload._put_multipart_upload ok, cost time:%s", time.time() - start_time)
        return result

    def cancel_multipart_upload(self, key, upload_id, headers=None):
        return self._bucket.abort_multipart_upload(key, upload_id, headers=headers)

    def get_video_frame_image(self, filename=None, url=None):
        """ 视频的第一帧图片
        :param filename: str, 本地文件路径名
        :param url: str 视频 url
        """
        tmp_img_filename = os.path.splitext(filename)[0] + ".jpg"
        cap = cv2.VideoCapture(filename)

        try:
            scu = cap.isOpened()
            success, frame = cap.read()
            cv2.imwrite(tmp_img_filename, frame)
        except Exception as e:
            self.logger.error("AliOssFileUpload => 获取视频第一帧图片失败, err:%s", e)
            self.logger.error(traceback.format_exc())

            return ""
        finally:
            cap.release()

        key = self._get_oss_key(tmp_img_filename)
        result = self._put_object(tmp_img_filename, key=key)  # 首帧图片上传aliyun

        oss_response = result.resp.response
        img_url = urllib.parse.unquote(oss_response.url)
        self.logger.info("AliOssFileUpload => frame image url:%s", img_url)

        os.remove(tmp_img_filename)  # 删除临时文件
        return img_url

    def _get_video_duration_and_style(self, filename):
        duration = -1
        screen_style = None  # landscape:横屏   vertical:竖屏
        cap = cv2.VideoCapture(filename)

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

    def check_anti_spam(self, url, is_frame_url=False):
        """ 反垃圾审查 """
        result = dict(img_url="", duration=0, screen_style=None, msg="ok")

        key = urllib.parse.urlparse(url).path
        file_type = self._get_file_type(filename=key)
        detect_method = self._get_check_method(file_type=file_type)
        filename = os.path.join(self.TMP_STORAGE_PATH, str(uuid.uuid1()) + os.path.splitext(key)[1])

        try:
            object_stream = self.get_object(key=key.lstrip("/"))
            byte_content = object_stream.read()

            if is_frame_url:
                with open(filename, "wb") as fp:
                    fp.write(byte_content)

                result["img_url"] = self.get_video_frame_image(filename)
                duration, screen_style = self._get_video_duration_and_style(filename)
                result.update(duration=duration, screen_style=screen_style)

                if duration == -1:
                    raise ValueError("视频时长解析失败")
                elif duration > self.MAX_VIDEO_DURATION:
                    raise ValueError("视频时长(%ss)已经超过 %ss" % (duration, self.MAX_VIDEO_DURATION))

            if self.ON_ANTI_SPAM_CHECK:
                detect_method(content=byte_content)
        except Exception as e:
            result["msg"] = str(e)
            self.logger.error("反垃圾审查 err:%s", e)
            self.logger.error(traceback.format_exc())
        finally:
            if os.path.exists(filename):
                os.remove(filename)

        return result

