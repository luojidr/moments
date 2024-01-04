import json
import base64
from itertools import groupby
from operator import itemgetter

from questionnaire.service import SurveyVoteService


def get_survey_data(raw_sql):
    return SurveyVoteService().get_sql_results(sql=raw_sql)


def get_user_dd_department(survey_id):
    dd_department = {}

    survey_user_input_sql = "select id, email, nickname from survey_user_input " \
                            "where survey_id=%s and email<>'' and email is not null" % survey_id
    db_survey_user_input_ret = get_survey_data(survey_user_input_sql)
    survey_user_input_dict = [dict(zip(['id', 'email', 'nickname'], items)) for items in db_survey_user_input_ret]

    if not survey_user_input_dict:
        return dd_department

    email_str = ', '.join(["'%s'" % d['email'] for d in survey_user_input_dict if d['email'] != '空'])
    hr_employee_sql = 'select id, name, mobile, email from hr_employee where active=true and email in (%s)' % email_str
    db_hr_employee_ret = get_survey_data(hr_employee_sql)
    hr_employee_dict = {item[3]: dict(zip(['id', 'name', 'mobile', 'email'], item)) for item in db_hr_employee_ret}

    if not db_hr_employee_ret:
        return dd_department

    department_sql = """
        select aa.name, cc.id from hr_department aa 
        join employee_department_multi_rel bb on aa.active=true and aa.id=bb.did 
        join hr_employee cc on cc.active=true and cc.id=bb.eid 
        where cc.id in (%s);
    """
    hr_employee_ids_str = ', '.join([str(e['id']) for e in hr_employee_dict.values()])
    db_department_ret = get_survey_data(department_sql % hr_employee_ids_str)
    department_dict = {item[1]: dict(zip(['name', 'employee_id'], item)) for item in db_department_ret}

    for item in survey_user_input_dict:
        user_input_id = item['id']
        email = item['email']
        nickname = item['nickname']

        employee = hr_employee_dict.get(email) or {}
        mobile = employee.get('mobile', '')
        employee_name = employee.get('name', nickname)

        department = department_dict.get(employee.get('id')) or {}
        department_name = department.get('name', '')

        dd_department[user_input_id] = [department_name, employee_name, mobile]

    return dd_department


def export_survey_detail(survey_id, is_required_user=False):
    """ Export survey to excel """
    values_list = []

    # 问题
    question_sql = "select id, title, question_type from survey_question where survey_id=%s ORDER BY ID"
    question_ret = get_survey_data(question_sql % survey_id)
    question_ids = [item[0] for item in question_ret]
    matrix_question_ids = [item[0] for item in question_ret if item[2] == "matrix"]
    question_type_dict = {item[0]: item[2] for item in question_ret}

    # 问题相关选项
    answer_option_sql = "SELECT id, value, value FROM survey_question_answer WHERE question_id in %s"
    answer_option_ret = get_survey_data(answer_option_sql % str(tuple(question_ids)))
    answer_option_dict = {item[0]: item[1] for item in answer_option_ret}

    answer_option_ret_sql = "SELECT id, matrix_question_id, value FROM survey_question_answer " \
                            "WHERE matrix_question_id in %s ORDER BY matrix_question_id"
    if matrix_question_ids:
        answer_option_matrix_ret = get_survey_data(answer_option_ret_sql % str(tuple(matrix_question_ids)))
    else:
        answer_option_matrix_ret = []
    group_answer_option_matrix_dict = {
        question_id: list(iterator)
        for question_id, iterator in groupby(answer_option_matrix_ret, key=itemgetter(1))
    }

    # ======== 添加excel标题 ========
    header = ["user_input_id"]
    order_question_or_matrix_list = [0]

    # 问卷回答者的基本信息
    if is_required_user:
        extra_user_headers = ["Department", "Name", "Mobile"]
        required_user_dict = get_user_dd_department(survey_id)
    else:
        extra_user_headers = []
        required_user_dict = {}

    header.extend(extra_user_headers)

    for q_item in question_ret:
        q_id = q_item[0]
        q_title = q_item[1]
        question_type = q_item[2]

        if question_type != "matrix":
            header.append(q_title)
            order_question_or_matrix_list.append(q_id)
        else:
            for matrix_row_item in group_answer_option_matrix_dict.get(q_id, []):
                matrix_row_id = matrix_row_item[0]
                matrix_row_title = matrix_row_item[2]

                header.append(q_title + "  " + matrix_row_title)
                order_question_or_matrix_list.append((q_id, matrix_row_id))
    else:
        values_list.append(header)

    # ====== 按照添加标题的顺序，将答案写入excel中。目前矩阵是单选， 如果多选请注意修改？？？======
    user_input_line_sql = "SELECT " \
                          "user_input_id, question_id, value_char_box, value_text_box, " \
                          "suggested_answer_id, matrix_row_id, value_numerical_box " \
                          "FROM survey_user_input_line WHERE survey_id=%s " \
                          "ORDER BY user_input_id, question_id"
    user_input_line_ret = get_survey_data(user_input_line_sql % survey_id)

    for user_input_id, iterator in groupby(user_input_line_ret, key=itemgetter(0)):
        values = [user_input_id]

        if is_required_user:
            name_mobile_list = required_user_dict.get(user_input_id, [])
            not name_mobile_list and name_mobile_list.extend(['', '', ''])
            values.extend(name_mobile_list)

        user_input_line_dict = {q_id: list(line_iter) for q_id, line_iter in groupby(iterator, key=itemgetter(1))}

        for _column, order_question_item in enumerate(order_question_or_matrix_list[1:], 1):
            if isinstance(order_question_item, int):
                question_id = order_question_item
            elif isinstance(order_question_item, (list, tuple)):
                question_id = order_question_item[0]
                matrix_row_id = order_question_item[1]
            else:
                raise ValueError("题目顺序错误")

            question_type = question_type_dict[question_id]
            user_input_line_items = user_input_line_dict.get(question_id)

            if not user_input_line_items:
                values.append('')
                continue

            if question_type == "simple_choice":
                suggested_answer_id = user_input_line_items[0][4]
                value = answer_option_dict.get(suggested_answer_id, "")

            elif question_type == "char_box":
                value = user_input_line_items[0][2]

            elif question_type == "text_box":
                value = user_input_line_items[0][3]

            elif question_type == "multiple_choice":
                suggested_answer_ids = [line_item[4] for line_item in user_input_line_items]
                answer_list = [answer_option_dict.get(sa_id, "") for sa_id in suggested_answer_ids]
                value = ", ".join(answer_list)
            elif question_type == "matrix":
                # 根据 question_id 和 matrix_row_id 确定答案
                line_suggested_answer_dict = {
                    (line_item[1], line_item[5]): line_item[4]
                    for line_item in user_input_line_items
                }

                key = (question_id, matrix_row_id)
                suggested_answer_id = line_suggested_answer_dict.get(key, 0)
                value = answer_option_dict.get(suggested_answer_id, "")
            elif question_type == "numerical_box":
                value = user_input_line_items[0][6]
            else:
                raise ValueError("题型错误")

            values.append(value)

        values_list.append(values)

    return values_list
