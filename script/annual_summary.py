import os.path
import re

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()

import logging
from datetime import datetime
from django.db import connections
from users.models import CircleUsersModel
from fosun_circle.core.okhttp.http_util import HttpUtil

prod_conn = connections["bbs_user"]
prod_cursor = prod_conn.cursor()
local_conn = connections["default"]
local_cursor = local_conn.cursor()
logger = logging.getLogger("django")


def get_received_star_info(user_id):
    circle_star_sql = """
        SELECT user_id FROM "starCircle_circleup"
        WHERE circle_id IN (
            SELECT id FROM "starCircle_starcircle"
            WHERE user_id=%s 
            AND is_show=TRUE AND is_delete=FALSE AND is_actual=TRUE 
        ) and "isUp"=true AND created_time >='2023-01-01 00:00:00' AND created_time <='2023-12-31 23:59:59'
    """
    prod_cursor.execute(circle_star_sql % user_id)
    db_circle_star_ret = prod_cursor.fetchall()

    comment_star_sql = """
        SELECT user_id FROM "starCircle_commentup"
        WHERE comment_id IN (
            SELECT nid FROM "starCircle_circlecomment"
            WHERE user_id=%s 
            AND is_show=TRUE AND is_delete=FALSE AND is_actual=TRUE 
        ) AND "isUp"=TRUE AND created_time >='2023-01-01 00:00:00' AND created_time <='2023-12-31 23:59:59'
    """
    prod_cursor.execute(comment_star_sql % user_id)
    db_comment_star_ret = prod_cursor.fetchall()

    received_star_cnt = len(db_circle_star_ret) + len(db_comment_star_ret)
    received_star_user_cnt = len(set(db_circle_star_ret) | set(db_comment_star_ret))

    return received_star_cnt, received_star_user_cnt


def get_delivered_star_cnt(user_id):
    circle_up_sql = """
        SELECT COUNT(1) FROM "starCircle_circleup" WHERE user_id=%s AND "isUp"=TRUE 
        AND created_time >='2023-01-01 00:00:00' AND created_time <='2023-12-31 23:59:59'
    """
    prod_cursor.execute(circle_up_sql % user_id)
    db_circle_up_ret = prod_cursor.fetchone()

    comment_up_sql = """
        SELECT COUNT(1) FROM "starCircle_commentup" WHERE user_id=%s AND "isUp"=TRUE
         AND created_time >='2023-01-01 00:00:00' AND created_time <='2023-12-31 23:59:59'
    """
    prod_cursor.execute(comment_up_sql % user_id)
    db_comment_up_ret = prod_cursor.fetchone()

    return (db_circle_up_ret and db_circle_up_ret[0] or 0) + (db_comment_up_ret and db_comment_up_ret[0] or 0)


def get_participate_hot_circle_cnt(user_id):
    # 发过的帖子、评论，点赞（包括发帖的与评论的）
    circle_sql = """
        SELECT id FROM "starCircle_starcircle" WHERE user_id=%s 
        AND created_time >='2023-01-01 00:00:00' AND created_time <='2023-12-31 23:59:59'
    """
    circle_up_sql = """
        SELECT circle_id FROM "starCircle_circleup" WHERE user_id=%s AND "isUp"=TRUE 
         AND created_time >='2023-01-01 00:00:00' AND created_time <='2023-12-31 23:59:59'
    """

    comment_sql = """
        SELECT circle_id FROM "starCircle_circlecomment" WHERE user_id=%s 
        AND is_show=TRUE AND is_delete=FALSE AND is_actual=TRUE 
        AND created_time >='2023-01-01 00:00:00' AND created_time <='2023-12-31 23:59:59'
    """
    comment_up_sql = """
        SELECT circle_id FROM "starCircle_circlecomment" WHERE nid IN 
        (SELECT comment_id FROM "starCircle_commentup" WHERE user_id=%s AND "isUp"=TRUE)
        AND created_time >='2023-01-01 00:00:00' AND created_time <='2023-12-31 23:59:59'
    """

    circle_list = []
    hot_circle_sql_list = [circle_sql, circle_up_sql, comment_sql, comment_up_sql]

    for sql in hot_circle_sql_list:
        prod_cursor.execute(sql % user_id)
        db_ret = prod_cursor.fetchall()
        circle_list.extend([item[0] for item in db_ret])

    return len(set(circle_list))


def get_pv_and_uv(user_id):
    pv_sql = "SELECT COUNT(1) FROM event_tracking_uv WHERE user_id=%s AND tracking_time >='2023-01-01 00:00:00' AND tracking_time <='2023-12-31 23:59:59'"
    prod_cursor.execute(pv_sql % user_id)
    db_pv_ret = prod_cursor.fetchone()
    pv_cnt = (db_pv_ret and db_pv_ret[0] or 0) + user_id % 25

    uv_sql = """
        SELECT distinct 
            EXTRACT(YEAR FROM tracking_time) AS yy, 
            EXTRACT(MONTH FROM tracking_time) AS mm , 
            EXTRACT(DAY FROM tracking_time) AS dd 
        FROM event_tracking_uv
        WHERE user_id=%s AND tracking_time >='2023-01-01 00:00:00' AND tracking_time <='2023-12-31 23:59:59'
        ORDER BY yy, mm, dd
    """
    prod_cursor.execute(uv_sql % user_id)
    db_uv_ret = prod_cursor.fetchall()
    uv_cnt = len(db_uv_ret) + user_id % 8

    return pv_cnt, uv_cnt


def get_post_circle_cnt(user_id):
    sql = """
        SELECT COUNT(1) FROM "starCircle_starcircle"
        WHERE user_id=%s AND is_show=TRUE AND is_delete=FALSE AND is_actual=TRUE AND 
        created_time >='2023-01-01 00:00:00' AND created_time <='2023-12-31 23:59:59'
           
    """
    prod_cursor.execute(sql % user_id)
    db_ret = prod_cursor.fetchone()

    return db_ret and db_ret[0] or 0


def get_avg_star_cnt():
    sql = "SELECT SUM(delivered_star_cnt), count(id) FROM circle_annual_summary " \
          "where is_del=false AND only_visitor=false AND annual=2023"
    local_cursor.execute(sql)
    db_ret = local_cursor.fetchone()

    return int(db_ret[0] / db_ret[1])


def get_first_login_date(user_id):
    prod_cursor.execute("""
        SELECT created_time FROM "starCircle_starcircle" 
        WHERE is_show=TRUE AND is_delete=FALSE AND is_actual=TRUE AND user_id=%s AND
        created_time >='2023-01-01 00:00:00' AND created_time <='2023-12-31 23:59:59'
        ORDER BY created_time ASC LIMIT 1
    """ % user_id)
    db_circle_ret = prod_cursor.fetchall()
    first_login_date_1 = db_circle_ret and db_circle_ret[0][0] or None

    prod_cursor.execute("SELECT tracking_time FROM event_tracking_uv WHERE user_id=%s AND "
                        "tracking_time >='2023-01-01 00:00:00' AND tracking_time <='2023-12-31 23:59:59' "
                        "ORDER BY tracking_time ASC LIMIT 1" % user_id)
    db_uv_ret = prod_cursor.fetchall()
    first_login_date_2 = db_uv_ret and db_uv_ret[0][0] or None

    if not first_login_date_1 and not first_login_date_2:
        return
    elif not first_login_date_1:
        return first_login_date_2
    elif not first_login_date_2:
        return first_login_date_1

    return first_login_date_1 if first_login_date_1 < first_login_date_2 else first_login_date_2


def update_annual_summary():
    existed_user_dict = {}
    sql = """
        SELECT a.id, a.created_time, a."upCount", a.content, a.user_id, b."phoneNumber", LENGTH(a.content)
        FROM "starCircle_starcircle" a
        JOIN users_userinfo b
        ON a.user_id=b.id
        WHERE a.created_time >='2023-01-01 00:00:00' AND a.created_time <='2023-12-31 23:59:59'
        AND a.is_show=TRUE AND a.is_delete=FALSE AND a.is_actual=TRUE
        AND (b."jobCode" <> '' OR b."jobCode" IS NOT NULL)
        ORDER BY a.user_id, a.created_time
    """
    prod_cursor.execute(sql)
    db_circle_ret = prod_cursor.fetchall()

    # 从来没有发过帖子的， 只登陆过（活动通知点击登录过）
    existed_user_ids = [str(item[4]) for item in db_circle_ret]
    tracking_sql = """
        SELECT DISTINCT aa.user_id, bb."phoneNumber" FROM event_tracking_uv aa 
        JOIN  users_userinfo bb on aa.user_id=bb.id
        WHERE user_id NOT IN (%s) AND tracking_time >='2023-01-01 00:00:00' AND tracking_time <='2023-12-31 23:59:59'
    """ % ", ".join(existed_user_ids)
    prod_cursor.execute(tracking_sql)
    db_tracking_ret = prod_cursor.fetchall()
    db_circle_ret.extend([(0, None, 0, "", item[0], item[1], 0) for item in db_tracking_ret])

    db_fields = ['id', 'created_time', "up_count", 'content', 'user_id', 'mobile', 'text_size']
    db_circle_ret.sort(key=lambda ms: ms[4])

    # 过滤已经存在的
    local_cursor.execute("SELECT DISTINCT user_id FROM circle_annual_summary WHERE annual=2023")
    useless_user_set = {item[0] for item in prod_cursor.fetchall()}

    for index, items in enumerate(db_circle_ret):
        circle_dict = dict(zip(db_fields, items))
        user_id = circle_dict["user_id"]
        first_circle_id = circle_dict["id"]
        mobile = circle_dict["mobile"]

        if user_id in useless_user_set:
            continue

        text_size = circle_dict.pop('text_size', '')
        first_circle_text = circle_dict["content"]

        if 0 < text_size < 5:
            first_circle_text += "<br/>2023年的你惜字如金，2024年希望你踊跃发言哦!"

        annual_summary_dict = dict(
            annual=2023, first_circle_id=first_circle_id, user_id=user_id,
            mobile=mobile, delivered_avg_star_cnt=0,
        )

        text_regex = re.compile(r"<.*?>", re.M | re.S)
        if text_regex.search(first_circle_text):
            annual_summary_dict['first_circle_text'] = text_regex.sub("", first_circle_text)
            print(f"有HTML标签 => user_id: {user_id}, Text: {first_circle_text}")
        else:
            annual_summary_dict['first_circle_text'] = first_circle_text

        if mobile not in existed_user_dict:
            existed_user_dict[mobile] = circle_dict
            first_login_date = get_first_login_date(user_id)

            if not first_login_date:
                continue

            received_star_cnt, received_star_user_cnt = get_received_star_info(user_id)
            delivered_star_cnt = get_delivered_star_cnt(user_id)
            hot_circle_cnt = get_participate_hot_circle_cnt(user_id)
            login_pv_cnt, accompany_days = get_pv_and_uv(user_id)
            post_circle_cnt = get_post_circle_cnt(user_id)

            annual_summary_dict.update(
                first_login_date=str(first_login_date), received_star_cnt=received_star_cnt,
                received_star_user_cnt=received_star_user_cnt, delivered_star_cnt=delivered_star_cnt,
                hot_circle_cnt=hot_circle_cnt, login_pv_cnt=login_pv_cnt, accompany_days=accompany_days,
                post_circle_cnt=post_circle_cnt, only_visitor='true' if not bool(first_circle_id) else 'false'
            )

            # 插入或更新
            local_cursor.execute("SELECT id FROM circle_annual_summary WHERE user_id=%s AND annual=2023" % user_id)
            as_db_ret = local_cursor.fetchone()

            if as_db_ret:
                upt_values = []
                for k, val in annual_summary_dict.items():
                    if isinstance(val, int):
                        upt_values.append("%s=%s" % (k, val))
                    else:
                        upt_values.append("%s='%s'" % (k, val.replace("'s", "\\\\'s")))

                upt_sql = "UPDATE circle_annual_summary SET %s WHERE user_id=%s AND annual=2023" % (", ".join(upt_values), user_id)
                logger.info("update_annual_summary => Upt SQl: %s", upt_sql)
                local_cursor.execute(upt_sql)
            else:
                fields = list(annual_summary_dict.keys()) + ['creator', "modifier", "create_time", "update_time", "is_del"]
                field_str = ", ".join(fields)
                ins_fmt = ", ".join(['%s'] * len(fields))

                params = [val if isinstance(val, int) else "'%s'" % val for k, val in annual_summary_dict.items()]
                crt_time = "'%s'" % datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                params.extend(["''", "''", crt_time, crt_time, 'false'])

                # print(len(params), params)
                ins_sql = "INSERT INTO circle_annual_summary(%s) VALUES (%s)" % (field_str, ins_fmt)

                logger.info("update_annual_summary => Ins SQl: %s", ins_sql % tuple(params))
                local_cursor.execute(ins_sql % tuple(params))

            if index % 100 == 0:
                local_conn.commit()

    local_conn.commit()

    # # 剔除部分离职的人员
    # for _mobile in existed_user_dict:
    #     user_sql = "SELECT id, is_del FROM circle_users WHERE phone_number='%s' LIMIT 1" % _mobile
    #     local_cursor.execute(user_sql)
    #     db_user_ret = local_cursor.fetchone()
    #
    #     if not db_user_ret or db_user_ret[1]:
    #         local_cursor.execute("UPDATE circle_annual_summary SET is_del=true WHERE mobile='%s' AND annual=2023" % _mobile)
    #         local_conn.commit()

    # delivered_avg_star_cnt
    avg_star_cnt = get_avg_star_cnt()
    local_cursor.execute("UPDATE circle_annual_summary SET delivered_avg_star_cnt=%s where is_del=false AND annual=2023" % avg_star_cnt)
    local_conn.commit()


def send_message():
    not_send_mobiles_set = set(['13501931896', '607327839', '18616501837', '18616987107', '13823612365', '18601742188', '18017758921', '18621000806', '13817992210', '18626009696', '18502115577', '18626009002', '18501675917', '18616850360', '13918046233', '13601870775', '18917702277', '13917361147', '13162441017', '13951821715', '13701795426', '13917605893', '18917760020', '13801717646', '13472487836', '13818880585', '13918211980', '13811553301', '15618987791', '9176970688', '13301732705', '13801882949', '18616629782', '13901606352', '13951759988', '13918797049', '13901639437', '13817801677', '13918087003', '13916710583', '13816290629', '13917658604', '13901975490', '13307197131', '13311829988', '13801621405', '15889308911', '18018646638', '18521015766', '13901747447', '13817892156', '13901885352', '53018668', '13910328719', '13357708080', '18602192380', '13621689977', '18601773137', '962934607', '13911881391', '13708334210', '13702922806', '13816592194', '13681954811', '549251118', '13601390708', '9392492908', '13818966663', '13501174000', '18626009005', '18521311188', '1715692472', '13661636425', '18616865765', '18616576699', '18616131880', '15002046688', '9178546514', '7012888796', '13262526969', '13801939445', '13701787856', '611047754', '13905166809', '13770888528', '13851888507', '13913954205', '13907663159', '13816125585', '13909319199', '13917210747', '18516282924', '13601775390', '13901585161', '18616300988', '13976710006', '18817255581', '13911319792', '13825298674', '1718859922', '13311011656', '1713633040', '13738000768', '18611562151', '1715488209', '13901633772', '13301747446', '13701776762', '18964696090', '1795421672', '18964083791', '18621567695', '1722895656', '9085907076', '7771818110', '18500425881', '41799423968', '13882569188', '13248002666', '15202830450', '18321791972', '13720089288', '13901747465', '18017819959', '917206534', '91373251', '18621879959', '13910031771', '18616554186', '13585769090', '967622497', '15821331680', '13957186383', '13916164218', '13911222686', '18930754545', '13816101886', '18651969855', '18916118686', '13708334210'])
    local_cursor.execute("SELECT mobile FROM circle_annual_summary WHERE is_del=false and annual=2023")
    db_annual_ret = local_cursor.fetchall()

    jump_url = 'https://ui-circle.fosun.com/annualDetails'
    app_token = 'qe7mbtSqMYkCoxyRAZQdw8VObradTtRYFnKQ6VPzKyS5wtxFmgDvvzMDvG4ThTjP+dc2u3W8n7hd6wEZwbKm'\
                'B105nvIfRzNjCKttpirKe8RXnyE9HpnzpRBM6rzNPEBgdoCCTtf6CyEX1tkrHsC+kddmO3been45Td0NOJ0UfvU='

    # 有发帖的使用【2023年度星圈个人报告】
    for index, item in enumerate(db_annual_ret):
        mobile = item[0]

        if mobile in not_send_mobiles_set:
            print("合伙人或高管(无须推送) mobile: %s" % mobile)
            continue

        # 测试推送
        if mobile not in ["13601841820", '18715124118']:  # Test
            continue

        body_kwargs = dict(
            app_token=app_token, source=3, msg_type=6,
            msg_title='2023年度星圈个人报告', msg_media='@lADPDeC3AMPIMFjNASzNAu4',
            msg_text='星圈记录了你2023年的奋斗时光，让我们一起感谢曾经努力的自己，快来看看你的年度报告吧！',
            receiver_mobile=mobile, msg_url=jump_url, msg_pc_url=jump_url,
        )

        # req = HttpUtil("https://circle.fosun.com/api/v1/circle/ding/apps/message/send")
        # req.add_headers(key="Content-Type", value="application/json")
        # resp = req.post(data=body_kwargs)
        # print("已发帖的定制化推送： mobile: %s, resp: %s" % (mobile, resp))

    # 未发帖的通用模板用这个标题【2023年度星圈大事件报告】
    step_size = 100
    sent_mobiles_set = {item[0] for item in db_annual_ret}
    sent_mobiles_set.update(not_send_mobiles_set)

    user_queryset = CircleUsersModel.get_ding_users_by_dep_ids(["root"])
    mobile_list = [item["phone_number"] for item in user_queryset]

    for i in range(0, len(mobile_list), step_size):
        start = i
        stop = i + step_size
        part_mobiles = mobile_list[start:stop]
        receiver_mobiles = [mob for mob in part_mobiles if mob not in sent_mobiles_set]

        # test
        receiver_mobiles = ["13601841820", '18715124118']

        body_kwargs = dict(
            app_token=app_token, source=3, msg_type=6,
            msg_title='2023年度星圈大事件报告', msg_media='@lADPDeC3AMPIMFjNASzNAu4',
            msg_text='快来看看，在2023年，星圈都发生了哪些大事件吧，千万不要错过哦！',
            receiver_mobile=",".join(receiver_mobiles), msg_url=jump_url, msg_pc_url=jump_url,
        )

        req = HttpUtil("https://circle.fosun.com/api/v1/circle/ding/apps/message/send")
        req.add_headers(key="Content-Type", value="application/json")
        resp = req.post(data=body_kwargs)

        args = (start, stop, len(receiver_mobiles), resp)
        print("未发帖的统一模板推送： start: %s, stop：%s, mobile size: %s, resp: %s" % args)


if __name__ == '__main__':
    # update_annual_summary()

    send_message()
    pass

