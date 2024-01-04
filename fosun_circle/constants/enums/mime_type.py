import enum


class EnumBase(enum.Enum):
    @property
    def type(self):
        return self.value[0]

    @property
    def format(self):
        return self.value[1]


@enum.unique
class MimeTypeEnum(EnumBase):
    GE = (0, "application/octet-stream")
    JPEG = (1, "image/jpeg")
    PNG = (2, "image/png")
    PDF = (3, "application/pdf")
    DOC = (4, "doc")
    DOCX = (5, "docx")

    @classmethod
    def get_choices(cls):
        return [(enum_val.type, enum_val.format) for enum_val in MimeTypeEnum._member_map_.values()]


