import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from aliyunsdkdysmsapi.request.v20170525.SendBatchSmsRequest import SendBatchSmsRequest
from fosun_circle.core.ali_oss.sms_message import AliSmsMessageRequest


sms_client = AliSmsMessageRequest(
    sign_name="复星iHR",
    template_code="SMS_248000038",
    template_params=None,
    region_id="cn-hangzhou",
    access_key_id="",
    access_key_secret="",
)

sms_client.send_sms(
    # phone_numbers=["13601841820", ],
    # params=[dict(cmp_years=88, join_days=999)],
    #
    phone_numbers=["13601841820", "13601841820"],
    params=[{u"cmp_years": 15, u"join_days": 222}],
    # params=[dict(cmp_years=98, join_days=998), dict(cmp_years=100, join_days=10000)],
)



import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

client = AcsClient("", "", 'cn-hangzhou')


def send_batch_sms(phoneList, templateParams, TemplateCode):
    signName = "复星iHR"
    signNameList = [signName for i in phoneList]
    # templateParamList = [templateParam for i in phoneList]
    templateParamList_json = json.dumps(templateParams)
    signNameList_json = json.dumps(signNameList)
    phoneList_json = json.dumps(phoneList)
    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('dysmsapi.aliyuncs.com')
    request.set_method('POST')
    request.set_protocol_type('https')  # https | http
    request.set_version('2017-05-25')
    request.set_action_name('SendBatchSms')

    request.add_query_param('RegionId', "cn-hangzhou")
    request.add_query_param('PhoneNumberJson', phoneList_json)
    request.add_query_param('SignNameJson', signNameList_json)
    request.add_query_param('TemplateCode', TemplateCode)
    request.add_query_param('TemplateParamJson', templateParamList_json)

    print(request._params)
    print(request._header)

    # response = client.do_action_with_exception(request)
    #
    # result = str(response, encoding='utf-8')
    # data = json.loads(result)
    # print(data)


# send_batch_sms(
#     phoneList=["13601841820", "13601841820"],
#     templateParams=[dict(cmp_years=1, join_days=111), dict(cmp_years=2, join_days=222)],
#     TemplateCode="SMS_248000038",
# )
