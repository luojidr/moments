import json
import uuid

from aliyunsdkvod.request.v20170321.CreateUploadVideoRequest import CreateUploadVideoRequest

from .base import AliOssBase

__all__ = ('AliVodUploadVideo', )


class AliVodUploadVideo(AliOssBase):
    """ 阿里云OSS点播 """
    CATEGORY_ID = 1000096308

    def __init__(self, **kwargs):
        self._request = CreateUploadVideoRequest()
        super().__init__(**kwargs)

    def _add_body(self, title, filename, description=None, tags=None):
        uid = str(uuid.uuid1()).replace('-', '')

        self._request.set_accept_format(self.ACCEPT_FORMAT)
        self._request.set_Title(title)

        if not filename:
            filename = '/opt/%s.mp4' % uid

        if description:
            self._request.set_Description(description)

        self._request.set_CoverURL('https://circle.fosun.com/vod/video/%s' % uid)

        if tags:
            self._request.set_Tags(', '.join(tags))
        else:
            self._request.set_Tags('circleAppBms')

        self._request.set_FileName(filename)
        self._request.set_CateId(self.CATEGORY_ID)
        self._request.set_accept_format('JSON')

    def create_upload_video(self, title, filename=None, description=None, tags=None, **kwargs):
        """ 获取音/视频上传地址和凭证 """
        # https://help.aliyun.com/zh/vod/developer-reference/media-upload#topic-1959684
        self._add_body(title, filename, description, tags)

        response = self._client.do_action_with_exception(self._request)
        ticket_data = json.loads(str(response, encoding='utf-8'))
        return ticket_data



