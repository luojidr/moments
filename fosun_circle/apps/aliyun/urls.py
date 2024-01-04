from django.urls import re_path

from . import views

# 为了符合swagger的展示方便，强烈建议在同一app内使用相同前缀
urlpatterns = []

api_urlpatterns = [
    # 阿里云发送短信
    re_path(r"^sms/send$", view=views.AliSmsSendApi.as_view(), name="ali_sms_send"),

    # 阿里云上传凭证
    re_path(r"^vod/ticket/get$", view=views.AliVodTicketApi.as_view(), name="ali_vod_ticket"),

    # 文件分片上传(A)
    re_path(r"^chunk/upload$", view=views.FileChunkUploadApi.as_view(), name="ali_chunk_upload_api"),

    # 文件分片上传后保存在阿里云OSS(B)
    re_path(r"^upload/completed$", view=views.CompletedFileUploadApi.as_view(), name="ali_completed_upload_api"),

    # 分片上传 Html (测试)
    re_path(r"^chunk/test$", view=views.FileChunkUploadView.as_view(), name="ali_chunk_upload_html"),

    # Ali OSS 视频上传
    re_path(r"^oss/video/upload$", view=views.AliOssUploadApi.as_view(), name="ali_oss_video_upload"),

    # 反垃圾审查
    re_path(r"^oss/anti-spam/check$", view=views.AliOssCheckAntiSpamApi.as_view(), name="ali_oss_anti_spam_check"),

    # 上传后的文件列表
    re_path(r"^static-file/list$", view=views.ListStaticFileUploadApi.as_view(), name="ali_static_upload_list_api"),

    # 上传文件详情
    re_path(r"^static-file/detail$", view=views.DetailStaticFileApi.as_view(), name="static_file_detail_h5"),

    # 视频点播(VOD)-获取音/视频上传地址和凭证
    re_path(r"^vod/CreateUploadVideo$", view=views.VodCreateUploadVideoApi.as_view(), name="vod_CreateUploadVideo_api"),

]


view_urlpatterns = [
    # 上传图片
    re_path(r"^static-file/upload$", view=views.StaticFileUploadView.as_view(), name="ali_static_upload_view"),

]
