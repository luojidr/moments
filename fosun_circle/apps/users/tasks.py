import json
import math
import traceback
from multiprocessing.dummy import Pool as ThreadPool

import requests
from django.db import connections, connection

from config.celery import celery_app
from users.models import (
    CircleUsersModel,
    CircleDepartmentModel,
    CircleUser2DepartmentModel,
)
from fosun_circle.libs.log import task_logger as logger
from fosun_circle.libs.decorators import to_retry
from fosun_circle.libs.token_helpers import TokenHelper
from fosun_circle.core.ding_talk.uuc import DingUser

CACHE_UUC_USER_VERSION = "user:uuc"
CACHE_UUC_USER_KEY = "circle:user:uuc:%s"


class DingUUCService:
    @to_retry
    def get_uuc_data_by_api(self, api, start_id, end_id, token=None):
        result = []
        form_data = dict(start_id=start_id, end_id=end_id)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
        }

        if token:
            form_data['token'] = token
        else:
            form_data.update(TokenHelper().get_token())

        url = "https://ihcm.fosun.com/fosun/v1.0/hr_sorgstructure_od/{api}/list".format(api=api)

        status_code, code, message = 500, 5000, 'ok'
        try:
            logger.info("get_uuc_data_by_api ==>> form_data: %s", form_data)
            resp = requests.post(url, data=json.dumps(form_data), headers=headers)
            data = resp.json()
            error = data.get('error')

            if error:
                logger.error("get_uuc_data_by_api data => err: %s", error)
            else:
                result = data.get("result") or []
                status_code = resp.status_code
                code, message = data.get("code"), data.get("message")
        except Exception:
            message = "Fetch data error from ihcm"
            logger.error(traceback.format_exc())

        log_args = (url, status_code, code, message, len(result))
        logger.info("get_uuc_data_by_api ==>> url: %s\nstatus_code: %s, code: %s, message: %s, Count: %s", *log_args)

        return result, status_code


def _sync_ding_users():
    """ 同步钉钉用户表 """
    curr_page = 1
    page_size = 1500
    max_page_cnt = 350

    start_id = 0
    end_id = start_id + page_size

    circle_user_queryset = CircleUsersModel.objects.all()
    circle_user_dict = {user_obj.phone_number: user_obj for user_obj in circle_user_queryset}

    circle_user_mobile_set = set(circle_user_dict.keys())
    odoo_user_mobile_set = set()

    bulk_create_user_dict = {}
    update_fields_list = []
    bulk_update_user_list = []

    is_total_ok = True

    while curr_page <= max_page_cnt:
        odoo_user_list, status_code = DingUUCService().get_uuc_data_by_api(api="employee", start_id=start_id, end_id=end_id)
        is_total_ok = status_code == 200 if is_total_ok else is_total_ok

        for odoo_user_item in odoo_user_list:
            mobile = odoo_user_item.get("mobile_1") or ""
            if not mobile:
                continue

            odoo_user_mobile_set.add(mobile)
            circle_user_obj = circle_user_dict.get(mobile)

            user_kwargs = dict(
                ding_job_code=odoo_user_item.get("job_code") or "", is_staff=True,
                is_del=False, is_active=True, employee_status=1, phone_number=mobile,
                state_code=odoo_user_item.get("state_code_1") or "", email=odoo_user_item.get("email") or "",
                position_chz=odoo_user_item.get("title_desc") or "", avatar=odoo_user_item.get("avatar") or "",
                position_eng=odoo_user_item.get("en_title_desc") or "", username=odoo_user_item.get("fullname") or "",
                usr_id=odoo_user_item.get("usr_id") or "", source="DB",
            )
            not update_fields_list and update_fields_list.extend(list(user_kwargs.keys()))

            if not circle_user_obj:
                circle_user_obj = CircleUsersModel(**user_kwargs)

                # 避免出现二次相同的手机号被创建
                # django.db.utils.IntegrityError: duplicate key value violates unique constraint
                # "circle_users_phone_number_2d12cc3d_uniq" DETAIL: Key (phone_number)=(xxxx) already exists.
                mobile not in bulk_create_user_dict and bulk_create_user_dict.update(mobile=circle_user_obj)
            else:
                circle_user_obj.__dict__.update(user_kwargs)
                bulk_update_user_list.append(circle_user_obj)

            circle_user_obj.set_password(CircleUsersModel.DEFAULT_PASSWORD)

        curr_page += 1
        start_id = end_id
        end_id = start_id + page_size

        # 批量创建
        if bulk_create_user_dict:
            CircleUsersModel.objects.bulk_create(list(bulk_create_user_dict.values()))
            bulk_create_user_dict.clear()

        # 批量更新
        if bulk_update_user_list:
            CircleUsersModel.objects.bulk_update(bulk_update_user_list, fields=update_fields_list)
            bulk_update_user_list = []

    # 删除已经弃用的用户信息(通过uuc接口校验)
    required_delete_mobile_set = circle_user_mobile_set - odoo_user_mobile_set

    # for uuc_mobile in required_delete_mobile_set:
    #     if CircleUsersModel.create_or_update_user_by_uuc(mobile=uuc_mobile):
    #         required_delete_mobile_set.remove(uuc_mobile)

    if is_total_ok:
        update_kwargs = dict(is_del=True, is_active=False, is_staff=False, employee_status=2)
        CircleUsersModel.objects.filter(phone_number__in=list(required_delete_mobile_set)).update(**update_kwargs)


def _sync_ding_department():
    """ 同步钉钉部门表 """
    conn = connections["default"]
    truncate_sql = "TRUNCATE circle_ding_department"
    cursor = conn.cursor()
    cursor.execute(truncate_sql)
    # cursor.commit()

    curr_page = 1
    page_size = 1000
    max_page_cnt = 65

    start_id = 0
    end_id = start_id + page_size
    bulk_create_department_list = []

    while curr_page <= max_page_cnt:
        odoo_department_list, _ = DingUUCService().get_uuc_data_by_api(api="dept", start_id=start_id, end_id=end_id)

        for odoo_department_item in odoo_department_list:
            is_alive = int(odoo_department_item.get("alive_flag") or "0")
            department_kwargs = dict(
                dep_name=odoo_department_item.get("name") or "",
                dep_id=odoo_department_item.get("dep_id") or "",
                parent_dep_id=odoo_department_item.get("parent_dep_id") or "",
                dep_only_code=odoo_department_item.get("dept_ucode") or "",
                dep_en_name=odoo_department_item.get("en_name") or "",
                name_path=odoo_department_item.get("name_path") or "",
                batch_no=odoo_department_item.get("batch_no") or "",
                is_alive=bool(is_alive), is_del=not bool(is_alive),
                display_order=int(odoo_department_item.get("disporder") or "0"),
            )

            circle_department_obj = CircleDepartmentModel(**department_kwargs)
            bulk_create_department_list.append(circle_department_obj)

        if bulk_create_department_list:
            CircleDepartmentModel.objects.bulk_create(bulk_create_department_list)
            bulk_create_department_list.clear()

        curr_page += 1
        start_id = end_id
        end_id = start_id + page_size


def _sync_ding_user_department_relation():
    """ 同步钉钉用户与部门关系表 """
    conn = connections["default"]
    truncate_sql = "TRUNCATE circle_user_department_relation"
    cursor = conn.cursor()
    cursor.execute(truncate_sql)
    # cursor.commit()

    curr_page = 1
    page_size = 1000
    max_page_cnt = 300

    start_id = 0
    end_id = start_id + page_size
    bulk_create_relation_list = []

    while curr_page <= max_page_cnt:
        odoo_relation_list, _ = DingUUCService().get_uuc_data_by_api(api="rel_map", start_id=start_id, end_id=end_id)

        for odoo_relation_item in odoo_relation_list:
            is_alive = int(odoo_relation_item.get("alive_flag") or "0")
            relation_kwargs = dict(
                usr_id=odoo_relation_item.get("usr_id") or "",
                dep_id=odoo_relation_item.get("dep_id") or "",
                first_dep=odoo_relation_item.get("firstdep") or "",
                batch_no=odoo_relation_item.get("batch_no") or "",
                is_alive=bool(is_alive), is_del=not bool(is_alive),
                display_order=int(odoo_relation_item.get("disporder") or "0"),
            )

            circle_relation_obj = CircleUser2DepartmentModel(**relation_kwargs)
            bulk_create_relation_list.append(circle_relation_obj)

        if bulk_create_relation_list:
            CircleUser2DepartmentModel.objects.bulk_create(bulk_create_relation_list)
            bulk_create_relation_list.clear()

        curr_page += 1
        start_id = end_id
        end_id = start_id + page_size


@celery_app.task
def sync_ding_user_and_department(*args, **kwargs):
    """ 同步钉钉部门表 (03:30) """
    _sync_ding_users()
    _sync_ding_department()
    _sync_ding_user_department_relation()


# @celery_app.task
def sync_user_dept_info(**kwargs):
    cursor = connection.cursor()
    get_usr_string = (lambda ms: ', '.join(["'%s'" % s for s in ms if s]))

    dep_sql = """
        SELECT b.usr_id, a.dep_id, a.dep_name, a.name_path FROM circle_ding_department a
        JOIN circle_user_department_relation b ON a.dep_id=b.dep_id
        WHERE b.usr_id IN (%s) ORDER BY a.display_order
    """

    step_size = 1000
    cursor.execute('SELECT COUNT(1) FROM circle_users  WHERE is_del=false')
    db_ret_user_cnt = cursor.fetchone()
    user_total_count = db_ret_user_cnt and db_ret_user_cnt[0] or 0
    user_total_pages = int(math.ceil(user_total_count / step_size))
    user_page = 1

    while user_page <= user_total_pages:
        user_params = ((user_page - 1) * step_size, step_size)
        user_sql = 'SELECT id, usr_id FROM circle_users  WHERE is_del=false ORDER BY ID OFFSET %s LIMIT %s'
        cursor.execute(user_sql, user_params)
        user_dict = {item[1]: item[0] for item in cursor.fetchall()}
        user_page += 1

        if not user_dict:
            continue

        cursor.execute(dep_sql % get_usr_string(user_dict.keys()))
        dep_dict = {item[0]: item[2] for item in cursor.fetchall()}

        for usr_id, _user_id in user_dict.items():
            dep_name = dep_dict.get(usr_id)
            if dep_name:
                cursor.execute('UPDATE circle_users SET department_chz=%s WHERE id=%s', (dep_name, _user_id))

        connection.commit()
