from enum import Enum


class SmsTypeEnum(Enum):
    LOGIN = (1, "login")
    CALL_NOTIFY = (2, "Call Notify")
    CALL_UPDATE = (3, "Call Update")
    CALL_START = (4, "Call Start")

    @property
    def type(self):
        return self.value[0]

    @property
    def name(self):
        return self.value[1]

    @classmethod
    def sms_check(cls, send_type):
        for e in iter(cls._member_map_.values()):
            if e.type == send_type:
                return True

        raise ValueError('短信发送类型错误<type: %s>' % send_type)
