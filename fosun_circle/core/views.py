from django.views.generic import ListView, TemplateView
from django.http.response import JsonResponse
from django.db.models.query import BaseIterable, QuerySet

__all__ = ["SingleVueView", "ListVueView"]


class BaseVueView(object):
    """ 后端管理: 先获取 Vue Html, 然后使用数据渲染Vue组件
    注意:
        (1): 先获取 Vue Html页面，通过 django 渲染成渲 template
        (2): 若 django template 需要被渲染的, 先渲染template, 然后获取 template Html
        (3): 若 django template 不需要渲染, 直接获取 template Html
        (4): 获取 Vue Html 中组件需要的数据, 返回 api 出参:
            {
                "html": `django_template_html`,
                "data": `vue_render_component_data`
            }
    """
    @property
    def page_offset(self):
        return self.__dict__.get("_offset", 0)

    @page_offset.setter
    def page_offset(self, value):
        self.__dict__["_offset"] = value

    @property
    def page_limit(self):
        return self.__dict__.get("_limit", 1)

    @page_limit.setter
    def page_limit(self, value):
        self.__dict__["_limit"] = value


class SingleVueView(TemplateView):
    """ 仅无数据时渲染模板页面 """
    model = None
    queryset = None

    def get_queryset(self):
        """ 渲染页面需要的数据 """

    def get(self, request, *args, **kwargs):
        if self.queryset is not None:
            queryset = self.queryset
        else:
            queryset = self.get_queryset()

            if not queryset and self.model:
                queryset = self.model.objects.all()

        if isinstance(queryset, (BaseIterable, QuerySet)):
            data = dict(list=[obj.to_dict() for obj in queryset])
        else:
            data = queryset

        template_response = super().get(request, *args, **kwargs)
        return JsonResponse(
            data=dict(
                data=data,
                html=template_response.rendered_content
            )
        )


class ListVueView(ListView, BaseVueView):
    # If template require data to render
    render_template = False

    def get_pagination_list(self):
        """ 渲染组件的分页数据 """
        raise NotImplementedError

    def get_component_list(self):
        """ 渲染组件的数据 """
        page = int(self.request.GET.get("page", 1))
        page_size = int(self.request.GET.get("page_size", 10))

        cls_name = self.__class__.__name__
        self.page_offset = (page - 1) * page_size
        self.page_limit = page_size
        data = self.get_pagination_list()

        if not isinstance(data, dict):
            raise ValueError("%s class method:get_pagination_list return data not dictionary", cls_name)

        total_count = data.pop("total_count", 0)
        vue_render_list = data.pop("list", [])

        return dict(
            list=vue_render_list, page=page,
            page_size=page_size, total_count=total_count,
            **data
        )

    def get(self, request, *args, **kwargs):
        if self.render_template:
            template_response = super().get(request, *args, **kwargs)
        else:
            self.object_list = None
            template_response = self.render_to_response(context=None)

        data = self.get_component_list()
        return JsonResponse(
            data=dict(
                data=data,
                html=template_response.rendered_content
            )
        )
