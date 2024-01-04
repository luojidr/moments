import os.path

from django.conf import settings
from django.views.generic import TemplateView
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage, FileSystemStorage
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.schemas import AutoSchema

import coreapi

from .service import AliOssUploadService
from config.conf.aliyun import FosunSmsConfig
from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.libs import callbacks
from fosun_circle.contrib.drf.throttling import ApiSMSStrictRateThrottle
from fosun_circle.constants.enums.sms_type import SmsTypeEnum
from fosun_circle.core.views import ListVueView, SingleVueView
from fosun_circle.core.ali_oss.sms_message import FosunSmsMessageRequest
from fosun_circle.core.ali_oss.vod import AliVodUploadVideo
from fosun_circle.apps.aliyun.tasks.task_check_oss_anti_spam import check_oss_anti_spam

from .forms import UploadStaticFileForm
from .models import AliStaticUploadModel
from .serializers import StaticUploadSerializer


class AliSmsSendApi(APIView):
    throttle_classes = (ApiSMSStrictRateThrottle, )
    permission_classes = [permissions.AllowAny]

    schema = AutoSchema(
        manual_fields=[
            coreapi.Field(name='send_type', required=True, location='form', description='发送类型', type='int'),
            coreapi.Field(name='phone_numbers', required=True, location='form', description='手机号', type='array'),
        ])

    def post(self, request, *args, **kwargs):
        """ 阿里云发送短信 """
        send_type = request.data.get('send_type')
        template_param = request.data.get('params')
        phone_numbers = request.data.get('phone_numbers')

        SmsTypeEnum.sms_check(send_type=send_type)
        if not phone_numbers:
            raise ValueError("手机号不能为空")

        sms_rets = FosunSmsMessageRequest(
            sign_name=FosunSmsConfig.SIGN_NAME
        ).send_sms(phone_numbers, send_type=send_type, template_param=template_param)

        return Response(data=sms_rets)


class AliVodTicketApi(APIView):
    schema = AutoSchema(
        manual_fields=[
            coreapi.Field(name='title', required=True, location='form', description='标题', type='string'),
            coreapi.Field(name='filename', required=True, location='form', description='上传的文件名', type='string'),
        ])

    def post(self, request, *args, **kwargs):
        """ 获取阿里云上传凭证 """


class AliOssUploadApi(APIView):
    def post(self, request, *args, **kwargs):
        """ 阿里云 OSS 上传(视频)"""
        if not request.FILES:
            raise FileNotFoundError("视频没有上传")

        tmp_upload_fd = request.FILES["video"]
        result = AliOssUploadService(callback=callbacks.update_post_callback).upload(tmp_upload_fd=tmp_upload_fd)

        return Response(data=result)


class AliOssCheckAntiSpamApi(APIView):
    def _check(self):
        method = self.request.method
        if method == "GET":
            data = self.request.query_params
        elif method == "POST":
            data = self.request.data
        else:
            data = {}

        check_oss_anti_spam.delay(uid=data.get("uid"))

    def get(self, request, *args, **kwargs):
        self._check()
        return Response(data=None)

    def post(self, request, *args, **kwargs):
        """ Oss 反垃圾审核 """
        self._check()
        return Response(data=None)


class FileChunkUploadView(TemplateView):
    template_name = "simulator_dev/chunk_upload.html"


class FileChunkUploadApi(APIView):
    LOCATION = '/tmp/aliyunUpload/'
    FILE_CHUNK_NAME = "{task_id}_{chunk_seq}"

    def post(self, request, *args, **kwargs):
        """ 文件分片上传(建议以 4Mb 作为一次分片) """
        upload_file = request.FILES["file"]
        _, ext = os.path.splitext(upload_file.name.lower())
        task_id = request.POST.get('task_id')               # 获取文件唯一标识符
        chunk_seq = request.POST.get('chunk', 0)            # 获取该分片在所有分片中的序号
        is_upload = request.POST.get('is_upload') in ['true', '1']           # 是否直接上传

        # 构成该分片唯一标识符
        save_chunk_filename = self.FILE_CHUNK_NAME.format(task_id=task_id, chunk_seq=chunk_seq)
        logger.info("FileChunkUploadApi => chunk_filename:%s", save_chunk_filename)

        # 保存分片到本地: 保存的目录在 LOCATION
        storage = FileSystemStorage(location=self.LOCATION)
        path = storage.save(save_chunk_filename, ContentFile(upload_file.read()))

        # 多POD(DOCKER), 请求可能不会打到同一个POD上
        if is_upload or settings.IS_DOCKER:
            name = request.POST.get('name') or task_id
            static_dict = CompletedFileUploadApi.upload_aliyun(task_id, ext, name=name)
            return Response(data=static_dict)

        return Response(data=path)


class CompletedFileUploadApi(APIView):
    @staticmethod
    def upload_aliyun(task_id, ext, name, **kwargs):
        # tmp_path = settings.MEDIA_ROOT
        tmp_path = FileChunkUploadApi.LOCATION
        tmp_filename = os.path.join(tmp_path, task_id + ext)

        chunk_filename_list = [
            chunk_name
            for dir_path, dir_names, filenames in os.walk(tmp_path)
            for chunk_name in filenames if dir_path == tmp_path and task_id in chunk_name
        ]
        chunk_filename_list.sort()

        with open(tmp_filename, 'wb') as fd:
            for chunk_name in chunk_filename_list:
                chunk_path = os.path.join(tmp_path, chunk_name)

                with open(chunk_path, "rb") as chunk_fd:
                    chunk_bytes = chunk_fd.read()
                    fd.write(chunk_bytes)

                os.remove(chunk_path)  # 删除该分片，节约空间

        logger.info('CompletedFileUploadApi => tmp_filename: %s, size: %s', tmp_filename, os.path.getsize(tmp_filename))
        upload_ali_ret = AliOssUploadService(callback=None).upload(tmp_filename, is_check=False)
        upload_data = dict(kwargs, **upload_ali_ret)
        form = UploadStaticFileForm(data=dict(name=name, **upload_data))

        if form.is_valid():
            static_obj = form.save()
            return static_obj.to_dict()

        raise ValueError("文件合并后上传阿里云失败, FilePath: %s" % tmp_filename)

    def post(self, request, *args, **kwargs):
        """ 文件分片上传合并 """
        task_id = request.data.pop('task_id', None)
        src_filename = request.data.get('filename', '')
        _, ext = os.path.splitext(src_filename.lower())

        if not settings.IS_DOCKER:
            # raise ValueError('Docker环境中文件再上传时已传至阿里云')

            static_dict = self.upload_aliyun(task_id, ext, **request.data)
            return Response(data=static_dict)

        return Response(data=None)


class StaticFileUploadView(ListVueView):
    template_name = "aliyun/image-upload-list.html"
    serializer_class = StaticUploadSerializer

    def get_pagination_list(self):
        message_queryset = AliStaticUploadModel.objects.filter(is_del=False, is_success=True).all()
        serializer = self.serializer_class(message_queryset[:10], many=True)

        return dict(list=serializer.data, total_count=message_queryset.count())


class ListStaticFileUploadApi(ListAPIView):
    serializer_class = StaticUploadSerializer

    def get_queryset(self):
        name = self.request.query_params.get("name")
        query = dict(is_del=False, is_success=True)

        if name:
            query['name__icontains'] = name

        return AliStaticUploadModel.objects.filter(**query).all()


class VodCreateUploadVideoApi(APIView):
    def get(self, request, *args, **kwargs):
        title = request.query_params.get('title')
        filename = request.query_params.get('filename')
        data = AliVodUploadVideo().create_upload_video(title=title, filename=filename)

        return Response(data=data)


class DetailStaticFileApi(RetrieveAPIView):
    """ 上传文件详情(关怀H5) """
    serializer_class = StaticUploadSerializer

    def get_object(self):
        file_id = self.request.query_params.get('file_id', 0)
        return AliStaticUploadModel.objects.get(id=file_id)

