from enum import Enum


class AliOssTypeEnum(Enum):
    IMAGE = (1, "image")
    FILE = (2, "file")
    VIDEO = (3, "video")
    VOICE = (4, "voice")
    TEXT = (5, "text")
    WEB_PAGE = (6, "webpage")

    @property
    def type(self):
        return self.value[0]

    @property
    def name(self):
        return self.value[1]

    @classmethod
    def get_name(cls, oss_type):
        for _enum in AliOssTypeEnum._member_map_.values():
            if _enum.type == oss_type:
                return _enum.name

        raise ValueError("oss_type: %s 不存在" % oss_type)

