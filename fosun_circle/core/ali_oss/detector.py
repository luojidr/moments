import uuid
import json
import time
from datetime import datetime

from aliyunsdkgreen.request.v20180509 import TextScanRequest
from aliyunsdkgreen.request.v20180509 import ImageSyncScanRequest
from aliyunsdkgreen.request.v20180509 import VideoAsyncScanRequest
from aliyunsdkgreenextension.request.extension import ClientUploader
from aliyunsdkgreenextension.request.extension import HttpContentHelper

from . import exceptions
from .base import AliOssBase
from fosun_circle.constants.enums.oss_type import AliOssTypeEnum

__all__ = ["AliScanDetector"]


class AliScanDetector(AliOssBase):
    """ 阿里文本、图片、视频、语音、网页审核
    (1): 提交图片同步检测任务，对图片进行多个风险场景的识别，
         包括色情、暴恐涉政、广告、二维码、不良场景、Logo（商标台标）识别
    """

    def _get_scan_request(self, req_type=AliOssTypeEnum.IMAGE.type):
        """
        :param req_type: 1 文件, 2 图片, 3 视频
        :return:
        """
        if req_type == AliOssTypeEnum.TEXT.type:
            scan_request_cls = TextScanRequest.TextScanRequest
        elif req_type == AliOssTypeEnum.IMAGE.type:
            scan_request_cls = ImageSyncScanRequest.ImageSyncScanRequest
        elif req_type == AliOssTypeEnum.VIDEO.type:
            scan_request_cls = VideoAsyncScanRequest.VideoAsyncScanRequest
        else:
            raise ValueError("阿里云扫描 request 不合法!")

        request = scan_request_cls()
        request.set_accept_format(self.ACCEPT_FORMAT)
        return request

    def detect_text(self, content):
        """ 文本反垃圾审核
        https://help.aliyun.com/document_detail/53436.html?spm=a2c4g.11186623.6.754.55362542wxRL4C
        """
        request = self._get_scan_request(req_type=AliOssTypeEnum.TEXT.type)
        task = dict(
            dataId=str(uuid.uuid1()), content=content,
            time=datetime.now().microsecond
        )
        # 文本反垃圾检测场景的场景参数是 antispam
        request.set_content(HttpContentHelper.toValue({"tasks": [task], "scenes": ["antispam"]}))
        return self._do_action(request)

    def detect_image(self, content):
        """ 图片反垃圾审核
        https://help.aliyun.com/document_detail/53432.html?spm=a2c4g.11186623.6.752.57567981axKU0M
        """
        request = self._get_scan_request(req_type=AliOssTypeEnum.IMAGE.type)
        uploader = ClientUploader.getImageClientUploader(self._client)
        url = uploader.uploadBytes(content)

        task = dict(dataId=str(uuid.uuid1()), url=url)
        request.set_content(HttpContentHelper.toValue({"tasks": [task], "scenes": ["porn"]}))

        return self._do_action(request)

    def detect_video(self, content):
        """ 视频审核
        https://help.aliyun.com/document_detail/53434.html
        """
        start_time = time.time()
        request = self._get_scan_request(req_type=AliOssTypeEnum.VIDEO.type)
        # 上传二进制文件到服务端。
        uploader = ClientUploader.getVideoClientUploader(self._client)
        url = uploader.uploadBytes(content)

        task = dict(dataId=str(uuid.uuid1()), url=url)
        request.set_content(HttpContentHelper.toValue({"tasks": [task], "scenes": ["terrorism"]}))

        if not self._do_action(request):
            self.logger.error("AliScanDetector.detect_video failed, cost time:%s", time.time() - start_time)
            raise exceptions.ContentRiskyError(msg="视频含有风险内容，检测不通过", code=6001)

        self.logger.info("AliScanDetector.detect_video ok, cost time:%s", time.time() - start_time)

    def _do_action(self, request):
        is_valid = False

        response = self._client.do_action_with_exception(request)
        result = json.loads(response)

        if 200 == result["code"]:
            task_results = result["data"]

            for task_result in task_results:
                self.logger.info("AliScanDetector._do_action => task_result:%s", task_result)

                if 200 == task_result["code"]:
                    is_valid = True
                    scene_results = task_result.get("results", [])

                    for scene_result in scene_results:
                        self.logger.info("AliScanDetector._do_action => scene_result:%s", scene_result)

                        scene = scene_result.get("scene", {})
                        is_valid = scene_result.get("suggestion") == "pass"

                        return is_valid

        return is_valid

