import logging
import os.path
import json
import traceback
from urllib.parse import quote

import paramiko
import requests
from requests_toolbelt import MultipartEncoder
import psycopg2

logger = logging.getLogger(__name__)
employee_resume_path = r"D:/data/Fosun_data/employee_resume.json"
employee_resume_bello_path = r"D:/data/Fosun_data/employee_resume_bello.json"


def get_all_bello_id():
    connection = psycopg2.connect(
        host="10.100.130.84",
        port=5432,
        user="odoo",
        password="Hardw0rk@me",
        database="CoreHR"
    )
    cursor = connection.cursor()
    select_sql = "SELECT badge, name, bello_id FROM intf_employee_bello_id"
    cursor.execute(select_sql)
    results = cursor.fetchall()

    cursor.close()
    connection.close()

    values = [[v.strip() for v in row_vals] for row_vals in results]
    keys = ["badge", "name", "bello_id"]

    return {items[0]: dict(zip(keys, items)) for items in values}


def get_employee_resume_list():
    if not os.path.exists(employee_resume_path):
        logger.warning("简历下载为空：%s" % employee_resume_path)
        return {}

    with open(employee_resume_path, "rb") as fp:
        employee_resume_data = json.loads(fp.read().decode("utf-8"))

    return employee_resume_data


def download_resume_files():
    hostname = "10.100.180.108"
    username = "heht@root@10.161.200.91"
    password = "hht121236"

    transport = paramiko.Transport((hostname, 2222))
    transport.connect(None, username, password)
    print(transport)
    valid_resume_count = 0

    employee_resume_data = get_employee_resume_list()

    sftp = paramiko.SFTPClient.from_transport(transport)
    base_path = "/home/resources/files"
    sftp.chdir(base_path)
    listdir = sftp.listdir()

    resume_dict = dict()
    existed_employee_dict = get_all_bello_id()

    for index,  dir_path in enumerate(listdir):
        employee_id = dir_path.split("-")[0].strip()
        employee_name = dir_path.split("-")[1].strip()

        # 表中已存在该员工
        if employee_id in existed_employee_dict:
            continue

        # 该员工简历已下载
        if employee_id in employee_resume_data:
            continue

        print("employee_id: %s, dir_path: %s" % (employee_id, dir_path))

        resume_path = base_path + "/" + dir_path
        sftp.chdir(resume_path)
        resume_name = ""

        for filename in sftp.listdir():
            # print(filename)
            if "简历" in filename or "resume" in filename.lower():
                resume_name = filename

        print("index: %s, employee_id: %s, resume name: %s" % (index, employee_id, resume_name))

        if resume_name:
            remote_path = resume_path + "/" + resume_name

            if employee_id not in resume_name:
                resume_name = employee_id + "-" + resume_name

            local_path = "D:/data/Fosun_resume/" + resume_name
            sftp.get(remote_path, local_path)
            resume_dict[employee_id] = dict(employee_id=employee_id, employee_name=employee_name, path=local_path)

            valid_resume_count += 1

    print("有效简历Count:", valid_resume_count)

    employee_resume_data.update(resume_dict)
    with open(r"D:/data/Fosun_data/employee_resume.json", "wb") as fp:
        fp.write(json.dumps(employee_resume_data).encode("utf-8"))

    sftp.close()


class BelloResumeAnalysis(object):
    TOKEN_API = "https://www.belloai.com/api/user/login"
    UPLOAD_API = "https://www.belloai.com/api/resume/create"
    PORTRAIT_API = "https://www.belloai.com/api/osr_resume/{bello_id}/portrait_preview"
    DETAIL_API = "https://www.belloai.com/api/resume/{bello_id}"

    # 古怪的简历、无效简历
    ODD_RESUME_LIST = [
        "000268-罗丰-简历.pdf",      # 手写简历
        "000319-陆清-简历.pdf",      # 手写简历
    ]

    def __init__(self):
        self._token = self._get_token()
        assert self._token is not None, "Bello token is error"

    def get_headers(self, h=None, is_form_json=True):
        headers = {"Authorization": "Bearer " + self._token}

        if is_form_json:
            headers.update({'Content-Type': 'application/json'})

        if h is not None:
            headers.update(h)

        return headers

    def _get_token(self):
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "email": "ta.com",
            "password": "bwKnMZGu"
        }

        res = requests.post(self.TOKEN_API, data=json.dumps(data), headers=headers)
        return res.json()["token"]

    def _get_bello_id_by_upload(self, resume_path):
        resume_name = os.path.basename(resume_path)
        payload = {'channel': 'kayang'}
        # files = {"path": (quote(resume_name), open(resume_path, "rb"))}
        files = {"file": (resume_name, open(resume_path, "rb"))}
        headers = self.get_headers(
            {'Check': 'True', 'accept-encoding': 'gzip, deflate, br'},
            is_form_json=False
        )

        # m = MultipartEncoder(fields=[
        #     ("file", (resume_name, open(resume_path, "rb")))
        # ])
        # res = requests.post(self.UPLOAD_API, data=m, headers=dict(headers, **{"Content-Type": m.content_type}))

        res = requests.post(self.UPLOAD_API, data=payload, headers=headers, files=files)
        data = res.json()
        logger.warning("Resume Path: {}, \n简历上传Bello服务结果：{}\n\n".format(resume_path, data))

        error = data.get("error") or {}
        if error.get("message") == "无效简历":
            return 0

        if data.get("similar_resume"):
            bello_id = data.get("similar_resume")[0]["id"]
        elif data.get("resume"):
            bello_id = data["resume"]["id"]
        else:
            bello_id = None

        if bello_id is None:
            raise ValueError("上传简历出错")

        return bello_id

    def parse_bello_to_file(self):
        """ Bello接口：上传简历，获取 bello_id """
        bello_resume_info = {}
        employee_resume_data = get_employee_resume_list()

        if not os.path.exists(employee_resume_bello_path):
            logger.warning("没有简历上传付Bello服务！！！")
        else:
            with open(employee_resume_bello_path, "rb") as fp:
                tmp_bello = json.loads(fp.read().decode("utf-8"))
                bello_resume_info.update(tmp_bello)

        for employee_id, items in employee_resume_data.items():
            resume_path = items["path"]
            employee_name = items["employee_name"]

            is_ok = False
            is_ignore = False
            _resume_name = os.path.basename(resume_path)

            for _ in range(3):
                try:
                    bello_id = self._get_bello_id_by_upload(resume_path)

                    if isinstance(bello_id, int) and bello_id == 0:
                        is_ignore = True
                        break
                    else:
                        bello_resume_info[employee_id] = dict(
                            employee_id=employee_id,
                            bello_id=bello_id,
                            employee_name=employee_name
                        )
                        is_ok = True
                        break
                except Exception as e:
                    # traceback.print_exc()
                    logger.error("Exception: {}".format(e))

            if is_ignore:
                continue

            if not is_ok:
                raise ValueError("上传简历到Bello错误!")

        # 保存到文件中
        with open(employee_resume_bello_path, "wb") as fp:
            fp.write(json.dumps(bello_resume_info).encode("utf-8"))

    def get_portrait_from_bello(self):
        """ Bello接口： 根据 bello_id，获取简历画像 """
        bello_list = []

        with open(employee_resume_bello_path, "rb") as fp:
            tmp_bello = json.loads(fp.read().decode("utf-8"))
            bello_list.extend(tmp_bello.values())

        # connection = psycopg2.connect(
        #     host="10.100.130.84",
        #     port=5432,
        #     user="odoo",
        #     password="Hardw0rk@me",
        #     database="CoreHR"
        # )

        connection = psycopg2.connect(
            host="127.0.0.1",
            port=5432,
            user="dingxt",
            password="dingxt20201210_Local",
            database="odoo_local"
        )

        cursor = connection.cursor()

        for bello_item in bello_list:
            badge = bello_item["employee_id"]
            name = bello_item["employee_name"]
            bello_id = bello_item["bello_id"]

            portrait_api = self.PORTRAIT_API.format(bello_id=bello_id)
            res = requests.get(portrait_api, headers=self.get_headers(is_form_json=True))

            if res.status_code == 200:
                bello_data = res.json()
                has_children = bello_data.get("has_children")

                if has_children:
                    for tag in bello_data["children"]:
                        tag_type = tag["name"]

                        for sub_tag in tag["tags"]:
                            tag_subtype = sub_tag["name"]

                            for n_tag in sub_tag["tag_values"]:
                                resume_tags = dict(
                                    badge=badge, name=name, bello_id=bello_id,
                                    tag=n_tag, tag_type=tag_type, tag_subtype=tag_subtype
                                )

                                portrait_sql = self._insert_portrait_sql(resume_tags)
                                print(portrait_sql)
                                cursor.execute(portrait_sql)
                                connection.commit()

            else:
                logger.warning("获取简历画像错误， bello_id：{}, error:{}".format(bello_id, res.text))

        cursor.close()
        connection.close()

    def insert_bello_id_sql(self):
        bello_list = []
        bello_id_sql = "INSERT INTO intf_employee_bello_id (badge, name, bello_id) " \
                       "VALUES ('{badge}', '{name}', '{bello_id}')"

        with open(employee_resume_bello_path, "rb") as fp:
            tmp_bello = json.loads(fp.read().decode("utf-8"))
            bello_list.extend(tmp_bello.values())

        # connection = psycopg2.connect(
        #     host="10.100.130.84",
        #     port=5432,
        #     user="odoo",
        #     password="Hardw0rk@me",
        #     database="CoreHR"
        # )

        connection = psycopg2.connect(
            host="127.0.0.1",
            port=5432,
            user="dingxt",
            password="dingxt20201210_Local",
            database="odoo_local"
        )

        cursor = connection.cursor()

        for bello_item in bello_list:
            badge = bello_item["employee_id"]
            name = bello_item["employee_name"]
            bello_id = bello_item["bello_id"]

            bello_id_item = dict(badge=badge, name=name, bello_id=bello_id)
            sql = bello_id_sql.format(**bello_id_item)
            print(sql)
            cursor.execute(sql)
            connection.commit()

        cursor.close()
        connection.close()

    def _insert_portrait_sql(self, item):
        portrait_sql = "INSERT INTO intf_employee_bello_tag (badge, name, bello_id, tag, tag_type, tag_subtype) " \
                       "VALUES ('{badge}', '{name}', '{bello_id}', '{tag}', '{tag_type}', '{tag_subtype}')"

        return portrait_sql.format(**item)

    def get_resume_keypoint_from_bello(self):
        """ Bello接口： 根据 bello_id，获取简历详情、亮点 """
        bello_list = []

        with open(employee_resume_bello_path, "rb") as fp:
            tmp_bello = json.loads(fp.read().decode("utf-8"))
            bello_list.extend(tmp_bello.values())

        # connection = psycopg2.connect(
        #     host="10.100.130.84",
        #     port=5432,
        #     user="odoo",
        #     password="Hardw0rk@me",
        #     database="CoreHR"
        # )

        connection = psycopg2.connect(
            host="127.0.0.1",
            port=5432,
            user="dingxt",
            password="dingxt20201210_Local",
            database="odoo_local"
        )

        cursor = connection.cursor()

        for bello_item in bello_list:
            badge = bello_item["employee_id"]
            name = bello_item["employee_name"]
            bello_id = bello_item["bello_id"]

            detail_api = self.DETAIL_API.format(bello_id=bello_id)
            res = requests.get(detail_api, headers=self.get_headers(is_form_json=True))

            if res.status_code == 200:
                detail_data = res.json()

                for advantage in detail_data.get("_advantages", []):
                    keypoint1 = dict(
                        badge=badge, name=name, bello_id=bello_id,
                        type="advantage", point_id=advantage.get("id") or "",
                        point_name=advantage.get("name") or "",
                        point_message=advantage.get("message") or "",
                        point_rank=advantage.get("rank")
                    )

                    keypoint1_sql = self._insert_keypoint_sql(keypoint1)
                    print(keypoint1_sql)
                    cursor.execute(keypoint1_sql)
                    connection.commit()

                for risk in detail_data.get("_risks"):
                    keypoint2 = dict(
                        badge=badge, name=name, bello_id=bello_id,
                        type="risk", point_id=risk.get("id") or "",
                        point_name=risk.get("name") or "",
                        point_message=risk.get("message") or "",
                        point_rank=risk.get("rank")
                    )

                    keypoint2_sql = self._insert_keypoint_sql(keypoint2)
                    print(keypoint2_sql)
                    cursor.execute(keypoint2_sql)
                    connection.commit()

            else:
                logger.warning("简历亮点错误, bello_id：{}, error:{}".format(bello_id, res.text))

        cursor.close()
        connection.close()

    def _insert_keypoint_sql(self, items):
        keypoint_sql = "INSERT INTO intf_employee_bello_key_point (badge, name, bello_id, type, point_id, point_name, point_message, point_rank) " \
                       "VALUES ('{badge}', '{name}', '{bello_id}', '{type}', '{point_id}', '{point_name}', '{point_message}', {point_rank})"

        return keypoint_sql.format(**items)


def get_all_tags_from_db():
    """ 获取生产所有已有的标签 """

    # 新增人员
    with open(employee_resume_bello_path, "rb") as fp:
        tmp_bello = json.loads(fp.read().decode("utf-8"))
        badge_list = list(tmp_bello.keys())

    # connection = psycopg2.connect(
    #     host="10.100.130.84",
    #     port=5432,
    #     user="odoo",
    #     password="Hardw0rk@me",
    #     database="CoreHR"
    # )

    connection = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        user="dingxt",
        password="dingxt20201210_Local",
        database="odoo_local"
    )

    cursor = connection.cursor()

    od_tags_sql = "SELECT name FROM od_tags"
    cursor.execute(od_tags_sql)
    od_tags_ret = cursor.fetchall()
    tags_set_from_db = set([it[0] for it in od_tags_ret])
    # print(tags_set_from_db)

    badge_list_str = ",".join(["'%s'" % s for s in badge_list])
    bello_tags_sql = "SELECT tag, tag_type FROM intf_employee_bello_tag WHERE badge in (%s)" % badge_list_str
    print(bello_tags_sql)

    cursor.execute(bello_tags_sql)
    bello_tags_ret = cursor.fetchall()
    bello_tags_dict = {k: v for k, v in bello_tags_ret}
    bello_tag_set_from_db = bello_tags_dict.keys()

    print(len(bello_tags_ret))
    print(len(bello_tag_set_from_db), len(bello_tags_dict))

    # od_tags的name必须唯一
    diff_set = bello_tag_set_from_db - tags_set_from_db
    print(diff_set)
    print(len(diff_set))
    print(bello_tag_set_from_db & tags_set_from_db)

    # #########################################################################
    # 标签插入到od_tags表中
    # PARENT_MAPPING = {"技能标签": 3461, "行业领域": 3460, "资质与能力": 3459, "教育背景": 3458, "基本标签": 3457}
    #     # for tag_name in diff_set:
    #     #     od_tags_sql = """INSERT INTO od_tags("name", tag_type, "order", active, hidden, source, parent_id) VALUES ('%s', 40, 100, true, false, 16, %s)""" % (tag_name, PARENT_MAPPING.get(bello_tags_dict.get(tag_name)))
    #     #     print(od_tags_sql)
    #     #     # cursor.execute(od_tags_sql)
    #     #     # connection.commit()
    #     #     # break
    # #########################################################################

    for badge in badge_list:
        if badge in ["013431", "000268", "005650", "011302", "006838", "011217", "011234"]:
            continue

        print("badge:", badge)

        # 获取手机号
        hr_sql = "SELECT mobile FROM hr_employee WHERE badge='%s' ORDER BY id DESC LIMIT 1" % badge
        cursor.execute(hr_sql)
        hr_ret = cursor.fetchall()
        if not hr_ret:continue
        mobile = hr_ret[0][0]

        # 根据手机号获取uuc_id
        uuc_sql = "SELECT id, usr_id FROM intf_uuc_user_working WHERE mobile_1='%s' ORDER BY id DESC LIMIT 1" % mobile
        cursor.execute(uuc_sql)
        uuc_ret = cursor.fetchall()
        if not uuc_ret:continue
        uuc_id = uuc_ret[0][0]
        usr_id = uuc_ret[0][1]

        # 获取 firstdep
        firstdep_sql = "SELECT firstdep FROM intf_uuc_user_job WHERE usr_id = '%s' and alive_flag='1' ORDER BY id DESC LIMIT 1" % usr_id
        cursor.execute(firstdep_sql)
        firstdep_ret = cursor.fetchall()
        if not firstdep_ret:continue
        firstdep = firstdep_ret[0][0]

        # 获取badge对应的所有标签
        bello_sql = "SELECT tag FROM intf_employee_bello_tag WHERE badge = '%s'" % badge
        cursor.execute(bello_sql)
        bello_ret = cursor.fetchall()
        badge_to_tag_list = ["'%s'" % s[0] for s in bello_ret]

        # 获取对应标签id
        tag_sql = "SELECT id FROM od_tags where name in (%s)" % ",".join(badge_to_tag_list)
        cursor.execute(tag_sql)
        tag_id_ret = cursor.fetchall()
        tag_id_list = [t[0] for t in tag_id_ret]

        # 标签已经存在
        _tag_ids = [str(_id) for _id in tag_id_list]
        existed_tag_sql = "SELECT tag_id FROM od_experts_tags WHERE uuc_user=%s AND tag_id IN (%s)" % (uuc_id, ", ".join(_tag_ids))
        print("existed_tag_sql:", existed_tag_sql)
        cursor.execute(existed_tag_sql)
        existed_tag_ret = cursor.fetchall()

        required_add_tag_ids = list(set(tag_id_list) - set([tid[0] for tid in existed_tag_ret]))
        print("required_add_tag_ids:", required_add_tag_ids)

        for tag_id in required_add_tag_ids:
            od_experts_tags_sql = """INSERT INTO od_experts_tags(uuc_user, tag_id, active, mobile, "count", "type", firstdep, create_date, write_date) VALUES (%s, %s, true, '%s', 0, '2', '%s', NOW(), NOW())""" % (uuc_id, tag_id, mobile, firstdep)
            print(od_experts_tags_sql)
            try:
                cursor.execute(od_experts_tags_sql)
                # connection.commit()
            except psycopg2.errors.UniqueViolation as e:
                print("\t uuc_user: %s, tag_id: %s duplicate, err: %s" % (uuc_id, tag_id, str(e)))
            except Exception as e:
                print("\t uuc_user: %s, tag_id: %s failed, err: %s" % (uuc_id, tag_id, str(e)))

        # 父级标签是否存在
        p_existed_tag_sql = "SELECT tag_id FROM od_experts_tags WHERE uuc_user=%s AND tag_id IN (3457, 3458, 3459, 3460, 3461)" % uuc_id
        print("p_existed_tag_sql:", p_existed_tag_sql)
        cursor.execute(p_existed_tag_sql)
        p_existed_tag_ret = cursor.fetchall()
        p_required_tag_ids = list(set([3457, 3458, 3459, 3460, 3461]) - set([pid[0] for pid in p_existed_tag_ret]))
        print("p_required_tag_ids:", p_required_tag_ids)

        for parent_tag_id in p_required_tag_ids:
            parent_tags_sql = """INSERT INTO od_experts_tags(uuc_user, tag_id, active, mobile, create_date, write_date) VALUES (%s, %s, true, '%s', NOW(), NOW())""" % (
                uuc_id, parent_tag_id, mobile)
            print(parent_tags_sql)

            try:
                cursor.execute(parent_tags_sql)
                # connection.commit()
            except psycopg2.errors.UniqueViolation as e:
                print("\t uuc_user: %s, tag_id: %s duplicate, err: %s" % (uuc_id, parent_tag_id, str(e)))
            except Exception as e:
                print("\t uuc_user: %s, tag_id: %s failed, err: %s" % (uuc_id, parent_tag_id, str(e)))

        # break

    cursor.close()
    connection.close()


if __name__ == "__main__":
    # 下载增量简历
    # download_resume_files()

    # bello_ana = BelloResumeAnalysis()
    # print(bello_ana._token)

    # 简历上传Bello,获取简历ID
    # bello_ana.parse_bello_to_file()

    # # (1): bello_id存到数据库
    # bello_ana.insert_bello_id_sql()

    # # (2): 简历画像
    # bello_ana.get_portrait_from_bello()

    # # (3): 简历亮点
    # bello_ana.get_resume_keypoint_from_bello()


    # # Test
    # get_all_tags_from_db()

    _bello_id = "5fed93e5399f860001c16849"      # 许耀峰

    # bello = BelloResumeAnalysis()
    # detail_api = bello.DETAIL_API.format(bello_id=_bello_id)
    # res = requests.get(detail_api, headers=bello.get_headers(is_form_json=True))
    #
    # print(json.dumps(res.json()))

    base_cont = ''
    ori_data = {'base_cont': base_cont, 'uid': int(1906270), 'pwd': str("r2KAwQ"), 'need_avatar': 1, "fname": "103534-许耀峰-简历.pdf"}
    ori_res = requests.post("http://47.105.180.203/api/parse", data=json.dumps(ori_data), auth=('admin', '2015'))
    print("------------------------")
    print(json.dumps(ori_res.json()))

