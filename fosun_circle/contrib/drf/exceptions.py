import logging
import traceback

from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler

from fosun_circle.libs.exception import BaseError
from fosun_circle.constants.enums.code_message import CodeMessageEnum
from fosun_circle.core.djcelery_helper.utils.watcher import TaskWatcher

logger = logging.getLogger("django")


def get_traceback(exc):
    """ 获取异常信息 """
    code = None

    # 自定义类的获取
    if isinstance(exc, BaseError):
        code, message = exc
    elif isinstance(exc, APIException):
        # rest_framework.exceptions.APIException 中抛出的异常
        message_list = []
        errors = exc.args[0].serializer.errors if hasattr(exc.args[0], "serializer") else {}

        for err_key, err_msg_list in errors.items():
            msg = err_key + " -> " + "|".join(err_msg_list)
            message_list.append(msg)

        message = "\n".join(message_list) or str(exc)
    else:
        exc_args = exc.args
        message = (exc_args[1] if len(exc_args) > 1 else exc_args[0]) if exc_args else str(exc)

    return code, message


def exception_handler(exc, context):
    """
    Custom exception handling
    :param exc: exception instance
    :param context: throw exception context
    :return: Response
    """
    view = context['view']
    logger.error("drf.exceptions.exception_handler -> view: %s, exc: %s", view, exc)

    response = drf_exception_handler(exc, context)
    code, message = get_traceback(exc)

    if response is None:
        code = code or CodeMessageEnum.INTERNAL_ERROR.code
    else:
        code = code or response.status_code

    logger.error("---------- drf.exceptions.exception_handler start ----------")
    TaskWatcher.send_dd_robot(
        title="BMS服务端(统一)告警",
        task_name='standard warning service of BMS'
    )
    logger.error(traceback.format_exc())
    logger.error("---------- drf.exceptions.exception_handler end -------------")

    response = Response(data=dict(code=code, message=message))
    return response

