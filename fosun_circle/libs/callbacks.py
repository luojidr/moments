import traceback

from django.db import connections
from rest_framework.exceptions import ValidationError

from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.libs.decorators import retry_with_dormancy


@retry_with_dormancy()
def update_post_callback(*args, **kwargs):
    logger.info("after_update_post_callback: args:%s, kwargs:%s", args, kwargs)

    conn = connections["bbs_user"]
    cursor = conn.cursor()

    error = kwargs.get("error", "")
    uid = kwargs.get("uid", "AbCd1234")

    cursor.execute('SELECT id FROM "starCircle_starcircle" WHERE uid=%s', (uid,))
    db_ret = cursor.fetchall()

    if not db_ret:
        raise ValidationError("视频的帖子不在库中(uid=%s)" % uid)

    sql = 'UPDATE "starCircle_starcircle" SET remark=%s, is_delete=%s, is_show=%s WHERE uid=%s'
    sql_params = (error, "true" if error else "false", "false" if error else "true", uid)

    try:
        cursor.execute(sql, sql_params)
        conn.commit()
    except:
        logger.error(traceback.format_exc())
