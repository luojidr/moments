import json
import os.path
from django.db import connections

from config.celery import celery_app
from fosun_circle.libs.log import task_logger as logger
from fosun_circle.core.ali_oss.upload import AliOssFileUploader


@celery_app.task
def check_oss_anti_spam(uid=None, **kwargs):
    """ Ali Oss 反垃圾审核 """
    logger.info("check_oss_anti_spam => uid:%s, kwargs:%s", uid, kwargs)

    if not uid:
        return dict(msg="uid is empty")

    conn = connections["bbs_user"]
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT aa.id AS circle_id, bb.url AS url FROM "starCircle_starcircle" aa
            JOIN "starCircle_circleimage" bb ON aa.id = bb.circle_id
            WHERE aa.is_delete=TRUE AND aa.uid=%s
        """, (uid, ))
    db_ret = cursor.fetchone()
    url = db_ret and db_ret[1] or None
    circle_id = db_ret and db_ret[0] or None

    if not url:
        return dict(msg="url is empty of db")

    _, ext = os.path.splitext(url)
    uploader = AliOssFileUploader()
    ret = uploader.check_anti_spam(url=url, is_frame_url=True)

    img_url = ret["img_url"]
    screen_style = ret["screen_style"]
    message = json.dumps(ret)

    cursor.execute('UPDATE "starCircle_starcircle" '
                   'SET remark=%s, is_delete=false, is_show=true, frame_img_url=%s, screen_style=%s '
                   'WHERE id=%s', (message, img_url, screen_style, circle_id))

    return ret



