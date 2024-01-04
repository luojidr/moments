import os, sys
import django

pkg_path = os.path.dirname(os.path.dirname(__file__))
sys.path.append(pkg_path)

os.environ.setdefault("APP_ENV", "PROD")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.%s" % os.getenv('APP_ENV', 'DEV').lower())
django.setup()

import uuid
import time
import json
import logging
import requests
from django.db import connections
from users.models import CircleUsersModel
from fosun_circle.libs.utils.crypto import AESCipher

logger = logging.getLogger('auto_test_bbs_login')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
logger.addHandler(ch)


def check_ding_user_login(mobiles=None):
    mobiles = mobiles or []
    headers = {
        'Content-Type': 'application/json'
    }
    salt_key = 'salt2d9v_xy5dmf3'
    bbs_host = 'https://fosunapi.focuth.com'
    user_queryset = CircleUsersModel.objects.filter(is_del=False).order_by('id').all()
    total_count = user_queryset.count()

    if mobiles:
        user_queryset = user_queryset.filter(phone_number__in=mobiles)

    failed_token_mobiles = set()
    failed_login_mobiles = set()
    success_login_mobiles = set()

    for index, item in enumerate(user_queryset.values('phone_number', 'username'), 1):
        mobile = item['phone_number']
        username = item['username']
        logger.warning('%s(共%s) =>正在测试当前用户<%s | %s>', index, total_count, mobile, username)

        text = '%s:%s:%s:%s' % (str(uuid.uuid1()), mobile, int(time.time() * 1000), str(uuid.uuid1()))
        ciphertext = AESCipher(key=salt_key).encrypt(text)
        data = json.dumps(dict(mobtsk=ciphertext))
        resp = requests.post(bbs_host + '/user/token', data=data, headers=headers)
        result = resp.json()

        if result.get('code') != 200:
            failed_token_mobiles.add(mobile)
            logger.error('\t钉钉用户<%s>获取token错误, Ret: %s', mobile, result)
            continue

        x_auth = result['token']
        r = requests.post(
            bbs_host + '/user/mobileDingLogin',
            data=json.dumps(dict(phoneNumber=mobile)),
            headers=dict(headers, **{'X-Auth': x_auth})
        )
        bbs_user = r.json()
        logger.warning('\t钉钉用户<%s %s>登录星圈成功\n\t\t\t%s\n', username, mobile, bbs_user)

        if bbs_user.get('code') == 200:
            success_login_mobiles.add(mobile)
        else:
            failed_login_mobiles.add(mobile)

    # 统计token失败率，登录成功率
    logger.warning('\n\n用户总数: %s', total_count)

    failed_token_rate = len(failed_token_mobiles) / total_count * 100
    logger.warning('获取Token失败用户数<手机号可能替换>: %s, 占全部用户: %.2f%%', len(failed_token_mobiles), failed_token_rate)

    failed_login_rate = len(failed_login_mobiles) / total_count * 100
    logger.warning('登录失败用户数: %s, 占全部用户: %.2f%%', len(failed_login_mobiles), failed_login_rate)

    failed_count = len(failed_token_mobiles) + len(failed_login_mobiles)
    success_login_rate0 = 100.0 - failed_login_rate - failed_token_rate
    logger.warning('登录成功用户数: %s, 占全部用户: %.2f%%', total_count - failed_count, success_login_rate0)

    # success_login_rate = len(success_login_mobiles) / total_count * 100
    # logger.warning('登录成功用户数: %s, 占全部用户: %.2f%%', len(success_login_mobiles), success_login_rate)


if __name__ == '__main__':
    cursor = connections['bbs_user'].cursor()
    cursor.execute('SELECT "phoneNumber" FROM users_userinfo')
    db_bbs_ret = cursor.fetchall()
    bbs_mobiles = [item[0] for item in db_bbs_ret]

    queryset = CircleUsersModel.objects.filter(is_del=False).values_list('phone_number', flat=True)
    db_diff_mobiles = list(set(queryset) - set(bbs_mobiles))

    logging.warning('钉钉模拟登陆人数：%s', len(db_diff_mobiles))

    check_ding_user_login(db_diff_mobiles)





