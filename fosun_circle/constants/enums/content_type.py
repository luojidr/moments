from enum import unique, Enum


@unique
class ContentTypeEnum(Enum):
    PNG = ("image/png", "png")
    SVG = ("image/svg+xml", "svg")
    JPG = ("image/jpeg", "jpg")
    JPEG = ("image/jpeg", "jpeg")
    PDF = ("application/pdf", "pdf")
    ZIP = ("application/zip", "zip")
    DOC = ("application/msword", "doc")
    XLS = ("application/vnd.ms-excel", "xls")
    PPT = ("application/vnd.ms-powerpoint", "ppt")
    DOCX = ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx")
    PPTX = ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx")

    @property
    def content_type(self):
        return self.value[0]

    @property
    def suffix(self):
        return self.value[1]

    @classmethod
    def iterator(cls):
        return iter(cls._member_map_.values())

