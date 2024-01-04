__all__ = ["ContentRiskyError", "OSSConfigureError"]


class BaseError(Exception):
    def __init__(self, msg, code=500):
        self.msg = msg
        self.code = code


class ContentRiskyError(BaseError):
    pass


class OSSConfigureError(BaseError):
    pass
