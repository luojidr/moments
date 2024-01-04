from enum import Enum


class DingMsgTypeEnum(Enum):
    TEXT = ("text", "文本消息")
    IMAGE = ("image", "图片消息")
    VOICE = ("voice", "语音消息")
    FILE = ("file", "文件消息")
    LINK = ("link", "链接消息")
    OA = ("oa", "OA 消息")
    MARKDOWN = ("markdown", "markdown 消息")
    ACTION_CARD = ("action_card", "action_card 消息")
    SINGLE_ACTION_CARD = ("action_card", "action_card 消息")
    BTN_ACTION_CARD = ("action_card", "action_card 消息")

    @property
    def msg_type(self):
        return self.value[0]

    @property
    def desc(self):
        return self.value[1]

    @classmethod
    def iterator(cls):
        return iter(cls._member_map_.values())

    @classmethod
    def get_items(cls):
        return [(e.msg_type, e.desc) for e in cls.iterator()]
