import os
import time
from retrying import retry

from django.contrib.auth import get_user_model
from django_redis import get_redis_connection

from .utils.crypto import AESCipher


def to_retry(f):
    return retry(stop_max_attempt_number=3)(f)


def retry_with_dormancy(retry_times=3, stop_max_delay=None, retry_seconds=3, **kwargs):
    """ 每次休眠 retry_seconds 秒, 重试 retry_times 次
    重试次数:
        stop_max_delay: None, 重试 retry_times 次, 休眠 retry_times - 1 次
        stop_max_delay： int, 重试 stop_max_delay // retry_seconds 次, 休眠 (stop_max_delay // retry_seconds) - 1 次

    :param retry_times:     int, 重试次数
    :param stop_max_delay:  int, 限制最长重试时间[秒] (从执行方法开始计算)
    :param retry_seconds:   int, 设置固定重试时间[秒], 即: 休眠 retry_seconds 秒
    """
    def wrap(f):
        return retry(
            stop_max_attempt_number=retry_times,
            stop_max_delay=stop_max_delay,
            wait_fixed=retry_seconds * 1000,
            **kwargs
        )(f)

    return wrap


def _check(token=None, name=None, salt_key=None, expire=5 * 60):
    expire = int(expire)

    if not token:
        raise ValueError("token cannot be empty.")

    if len(token) <= 32:
        raise ValueError("token is valid.")

    token_key = os.environ.get(salt_key or 'API_TOKEN_KEY', "salt2d9v_xy5dmf3")
    aes = AESCipher(key=token_key)

    try:
        plain_text = aes.decrypt(token)
    except Exception:
        plain_text = None

    if not plain_text:
        raise ValueError("Illegal invoke, may be the token of attack")

    redis_conn = get_redis_connection()
    redis_key = 'api_token: %s' % token
    is_used = redis_conn.get(redis_key)

    if is_used:
        raise ValueError("token has been used.")

    plain_list = plain_text.split(':')
    timestamp = int(plain_list[2])
    valid_projects = plain_list[1].split(",")

    if (timestamp + expire) < int(time.time()):
        raise ValueError('token is expired, it is unusable')

    if not name or name not in valid_projects:
        raise ValueError('Illegal project to invoke.')

    # 验证合法人员
    mobile = plain_list[0]
    UserModel = get_user_model()
    user = UserModel.objects.filter(phone_number=mobile, is_del=False).first()

    if not user:
        raise ValueError("No permission to invoke this api")

    redis_conn.set(redis_key, 1, ex=expire)


def check_token(token=None, name=None, salt_key=None):
    def wrap(f):
        def validate(request, *args, **kwargs):
            if not request:
                raise ValueError("request is valid")

            data = request.query_params or request.data
            _check(token=data.get('token'), name=data.get('name'), salt_key=salt_key)

            return f(*args, **kwargs)
        return validate

    if token:
        return _check(token, name, salt_key)
    return wrap
