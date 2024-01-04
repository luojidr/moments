import os, sys
import logging
import psycopg2
import django

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logging.warning("BBS User Script Path: %s\n", path)
sys.path.append(path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from fosun_circle.core.ding_talk.uuc import DingUser

logger = logging.getLogger('auto_test_bbs_login')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
logger.addHandler(ch)


def sync_bbs_user():
    connection = psycopg2.connect(
        host="pgm-uf6525d859jun5329o.pg.rds.aliyuncs.com",
        port=5432,
        user="fosun_circle_bbs",
        password="gLsxPj36cie1",
        database="fosun_circle_bbs"
    )
    cursor = connection.cursor()

    cursor.execute('SELECT id, "phoneNumber" FROM users_userinfo')
    bbs_user_ret = cursor.fetchall()

    for index, item in enumerate(bbs_user_ret, 1):
        pk = item[0]
        mobile = item[1]

        if not mobile:
            continue

        logger.info('BBS User Index: %s, id: %s, mobile: %s', index, pk, mobile)

        try:
            ding_user = DingUser(mobile).get_ding_user()
            email = ding_user.get('email', '')
            avatar = ding_user.get('avatar', '')
            username = ding_user.get('name', '')

            logger.info('\t\t username: %s, email: %s, avatar: %s', username, email, avatar)
        except:
            pass


if __name__ == '__main__':
    sync_bbs_user()


