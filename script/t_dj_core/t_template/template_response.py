import os.path
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.http.request import HttpRequest
from django.template.response import TemplateResponse


def render():
    request = HttpRequest()
    tr = TemplateResponse(request,
                          template=["ding_talk/ding_message_list.html"],
                          )
    tr.render()


if __name__ == "__main__":
    render()
