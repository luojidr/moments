

class AliOssConfig(object):
    ACCESS_KEY_ID = ''
    ACCESS_KEY_SECRET = ''

    BUCKET_NAME = 'exerlalnd'
    ENDPOINT = "https://oss-cn-shanghai.aliyuncs.com"

    # Image bucket key
    IMAGE_BUCKET_KEY = "exerland-wechat/resource/image"

    # video bucket key
    VIDEO_BUCKET_KEY = "video_bbs"

    SMS_TEMPLATE_CODE = 'SMS_186610523'
    ALLOW_SUFFIX_LIST = ['jpg', 'jpeg', 'png', 'svg']
    CHZ_SIGN_NAME = '炼星球'
    CHZ_TEMPLATE_CODE = 'SMS_180052993'
    INTERNAL_SIGN_NAME = 'Focuth'
    INTERNAL_TEMPLATE_CODE = 'SMS_187561055'

    SMS_SIGN_NAME_DIGITAL = "复星数智"
    SMS_TEMPLATE_CODE_DIGITAL = "SMS_205440828"


class FosunSmsConfig:
    SIGN_NAME = '星圈'
    SIGN_CODE = 'sign_87963392'
    ACCESS_KEY_ID = 'oZerwjIYH5zNQLaT'
    ACCESS_KEY_SECRET = '3Xj8H31moot6ysauOVGAaZNG7YRWQJex'

    VERSION = "1.0.0"
    ACCEPT_FORMAT = "json"
    PROTOCOL_TYPE = "https"
    SMS_DOMAIN = "api-hpub.fosun.com"

    SMS_ONE_API = '/sms-api/sms/send'
    LOGIN_TEMPLATE_CODE = 'tmp_28477440'
    CALL_NOTIFY_TEMPLATE_CODE = 'tmp_68753152'
    CALL_UPDATE_TEMPLATE_CODE = 'tmp_76282368'
    CALL_START_TEMPLATE_CODE = 'tmp_91429632'
