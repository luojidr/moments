from enum import unique
from enum import Enum


class EnumBase(Enum):
    @property
    def code(self):
        return self.value[0]

    @property
    def message(self):
        return self.value[1]


@unique
class CodeMessageEnum(EnumBase):
    OK_200 = (200, "success")
    INTERNAL_ERROR = (1001, "程序内部异常")
    LOGIN_AUTH_FAIL = (1002, "用户名或密码错误")

    ALI_SMS_OK = (2000, "阿里云发送短信成功")
    ALI_SMS_ERROR = (2001, "阿里云发送短信错误")

    ALI_VOD_OK = (2020, "阿里云Vod Ticket获取成功"),
    ALI_VOD_ERROR = (2021, "阿里云Vod Ticket获取失败"),

    SERIALIZER_NOT_EXIST = (2040, "<RequestParamsBase>请求序列化类不存在")

    DING_MSG_TYPE_NOT_EXIST = (2060, "您发送的钉钉消息类型<{msg_type}>不存在")
    DING_MSG_BODY_FIELD_ERROR = (2064, "钉钉<{msg_type}>消息体字段错误")
    PHONE_VALIDATE_ERROR = (2061, "该手机号不合法:非大陆手机")
    UUC_USER_NOT_EXIST_ERROR = (2062, "手机号: %s, 无法从uuc接口获取钉钉用户")
    SMS_CODE_ERROR = (2063, "验证码错误")

    VALIDATION_ERROR = (2070, "%s")
    OBJECT_TYPE_NOT_MATCH = (2071, "【%s】模型对象类型不匹配")

    CREATE_BUCKET_ACCOUNT = (3001, "创建 Bucket Account Key 失败")

    INVALID_TOKEN = (4001, "非法Token")
    EXPIRED_TOKEN = (4002, "过期Token")
    URI_FORBIDDEN = (4003, "Url无权限调用")


if __name__ == "__main__":
    print(CodeMessageEnum.OK_200, type(CodeMessageEnum.OK_200))
    # print(CodeMessageEnum.OK_200.message)


