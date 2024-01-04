from bson import ObjectId
from django import forms

from .models import AliStaticUploadModel


class UploadStaticFileForm(forms.ModelForm):
    class Meta:
        model = AliStaticUploadModel
        fields = model.fields(exclude=['id'])

    def clean(self):
        self.cleaned_data["is_success"] = True
        self.cleaned_data["access_token"] = ObjectId().__str__()

        # 部分或全部字段引用模型的字段, 如果form中未显性声明为非必填, 则后续校验通不过，无法保存到数据库中
        self.errors.clear()

        return self.cleaned_data
