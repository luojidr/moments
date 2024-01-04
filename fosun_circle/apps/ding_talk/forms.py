import string
import random

from bson import ObjectId
from django import forms
from django.core.exceptions import ValidationError


from .models import DingAppMediaModel
from fosun_circle.libs.utils.crypto import BaseCipher


class UploadDingMediaForm(forms.ModelForm):
    # media = forms.FileField(max_length=256, help_text="源文件")
    # is_public = forms.BooleanField(required=False, initial=True, help_text="是否共享")

    class Meta:
        model = DingAppMediaModel
        exclude = model.deprecated_fields() + ["media_url", "post_filename"]

    def clean(self):
        # `media` type: django.core.files.uploadedfile:InMemoryUploadedFile
        media = self.cleaned_data["media"]

        self.cleaned_data["file_size"] = media.size
        self.cleaned_data["src_filename"] = media.name
        self.cleaned_data["key"] = ObjectId().__str__()
        self.cleaned_data["access_token"] = self._auto_access_token()
        self.cleaned_data["check_sum"] = BaseCipher.crypt_md5(media.file.read())

        # 部分或全部字段引用模型的字段, 如果form中未显性声明为非必填, 则后续校验通不过，无法保存到数据库中
        self.errors.clear()
        return self.cleaned_data

    def _auto_access_token(self, k=16):
        # 有一定概率冲突
        # access_token = "".join([random.choice(string.ascii_letters + string.digits) for _ in range(k)])
        return ObjectId().__str__()
