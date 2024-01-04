import json
import random
import string

from django.db.models import Q

from rest_framework import mixins
from rest_framework import views
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView

from fosun_circle.core.views import ListVueView
from circle.service import CircleBBSService
from .models import EsgEntryUserModel, ESGEntryDepartmentModel, ESGTaskActionModel
from .serializers import (
    ESGEntryDepartmentSerializer,
    DepartmentSerializer,
    ESGUserAdminSerializer,
    ESGTaskActionSerializer,
)
from fosun_circle.contrib.drf.throttling import ApiClientStrictRateThrottle
from .service import ESGService


class OperateEntryDepartmentApi(mixins.CreateModelMixin,
                                mixins.UpdateModelMixin,
                                GenericAPIView):
    serializer_class = ESGEntryDepartmentSerializer

    def post(self, request, *args, **kwargs):
        """ Create, Update, Delete """
        action = request.data.pop('action', None)
        assert action in ['create', 'update', 'delete'], 'Entry API Action Error!'

        if action != 'create':
            kwargs['partial'] = True

        if action == 'create':
            return self.create(request, *args, **kwargs)

        upt_attrs = {}
        pk = request.data.get('id')

        if action == 'delete':
            upt_attrs = dict(is_del=True)
        elif action == 'update':
            upt_attrs = dict(is_active=request.data.get('is_active', True))

        self.serializer_class.Meta.model.objects.filter(id=pk).update(**upt_attrs)
        return Response()


class EntryUserPermissionApi(views.APIView):
    throttle_classes = (ApiClientStrictRateThrottle, )

    def get(self, request, *args, **kwargs):
        mobile = request.query_params.get('mobile')
        entry_auth = EsgEntryUserModel.get_entry_user_permission(mobile)

        dep_list = entry_auth.get('dep_list', [])
        return Response(data=json.dumps(dep_list, indent=4, ensure_ascii=False))


class ListDepartmentApi(ListAPIView):
    serializer_class = DepartmentSerializer

    def get_queryset(self):
        key = self.request.query_params.get('key')
        query = dict(is_del=False, is_alive=True)
        queryset = self.serializer_class.Meta.model.objects.filter(**query).all()

        if key:
            queryset = queryset.filter(dep_name__icontains=key).all()

        return queryset.order_by('display_order').all()


class ListEntryDepartmentApi(ListAPIView):
    serializer_class = ESGEntryDepartmentSerializer

    def get_queryset(self):
        query = dict(is_del=False)
        queryset = self.serializer_class.Meta.model.objects.filter(**query).all()

        return queryset.order_by('-is_active', '-id').all()


class ListUserAdminApi(ListAPIView):
    serializer_class = ESGUserAdminSerializer

    def get_queryset(self):
        request = getattr(self, 'request', None)
        query_params = getattr(request, 'query_params', {})
        user_id = query_params.get('user_id')
        queryset = self.serializer_class.Meta.model.objects.filter(is_del=False).all()

        if user_id:
            queryset = queryset.filter(user_id=user_id).all()

        return queryset


class OperateUserAdminApi(mixins.CreateModelMixin,
                          mixins.UpdateModelMixin,
                          GenericAPIView):
    serializer_class = ESGUserAdminSerializer

    def get_object(self):
        pk = self.request.data.get('id')
        return self.serializer_class.Meta.model.objects.get(id=pk)

    def post(self, request, *args, **kwargs):
        """ Create, Update, Delete """
        action = request.data.pop('action', None)
        assert action in ['create', 'update', 'delete'], 'Operate User Admin API Action Error!'

        if action == 'create':
            return self.create(request, *args, **kwargs)

        if action == 'delete':
            instance = self.get_object()
            instance.is_del = True
            instance.save()
            return Response()

        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class ListTaskActionApi(ListAPIView):
    serializer_class = ESGTaskActionSerializer

    def get_queryset(self):
        request = getattr(self, 'request', None)
        query_params = getattr(request, 'query_params', {})

        key = query_params.get('key')
        tag_id = query_params.get('tag_id')
        queryset = self.serializer_class.Meta.model.objects.filter(is_del=False).all()

        if key:
            queryset = queryset.filter(name__icontains=key).all()

        if tag_id:
            queryset = queryset.filter(tag_id=tag_id).all()

        return queryset


class OperateTaskActionApi(mixins.CreateModelMixin,
                           mixins.UpdateModelMixin,
                           GenericAPIView):
    serializer_class = ESGTaskActionSerializer

    def get_object(self):
        pk = self.request.data.get('id')
        return self.serializer_class.Meta.model.objects.get(id=pk)

    def post(self, request, *args, **kwargs):
        """ Create, Update, Delete """
        action = request.data.pop('action', None)
        assert action in ['create', 'update', 'delete'], 'Operate ESG API Action Error!'

        if action == 'create':
            max_times = 100
            uid_set = set(self.serializer_class.Meta.model.objects.values_list('task_id', flat=True))

            while max_times:
                max_times -= 1
                task_id = "".join(random.choices(string.digits + string.ascii_letters, k=8))

                if task_id not in uid_set:
                    request.data['task_id'] = task_id
                    break

            return self.create(request, *args, **kwargs)

        if action == 'delete':
            instance = self.get_object()
            instance.is_del = True
            instance.save()
            return Response()

        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class TaskActionTipsApi(RetrieveAPIView):
    serializer_class = ESGTaskActionSerializer

    def get_object(self):
        task_id = self.request.query_params.get('task_id')
        query = dict(task_id=task_id, is_del=False)
        instance = self.serializer_class.Meta.model.objects.filter(**query).first()

        return instance


class CallbackAfterPostedApi(views.APIView):
    def post(self, request, *args, **kwargs):
        """ ESG发帖后将发帖数据回调给ESG后台 """
        mobile = request.data.get('mobile')
        quest_id = request.data.get('quest_id')
        circle_id = request.data.get('circle_id')

        data_kw = dict(mobile=mobile, circle_id=circle_id, quest_id=quest_id)
        callback_ret = ESGService().invoke_callback_after_posted(**data_kw)

        if not callback_ret['is_ok']:
            raise ValueError(callback_ret['msg'])

        return Response(data=None)


class EntryDepartmentView(ListVueView):
    template_name = 'esg/entry_department.html'

    def get_pagination_list(self):
        queryset = ListEntryDepartmentApi().get_queryset()
        serializer = ListEntryDepartmentApi.serializer_class(queryset[:10], many=True)

        return dict(list=serializer.data, total_count=queryset.count())


class UserAdminView(ListVueView):
    template_name = 'esg/user_admin.html'

    def get_pagination_list(self):
        queryset = ListUserAdminApi().get_queryset()
        serializer = ListUserAdminApi.serializer_class(queryset[:10], many=True)

        permission_type_list = [
            dict(zip(['id', 'name'], item))
            for item in ListUserAdminApi.serializer_class.Meta.model.PERMISSION_TYPE_CHOICES
        ]
        return dict(
            permission_type_list=permission_type_list,
            list=serializer.data, total_count=queryset.count()
        )


class TaskActionView(ListVueView):
    template_name = 'esg/task_action.html'

    def get_pagination_list(self):
        queryset = ListTaskActionApi().get_queryset()
        serializer = ListTaskActionApi.serializer_class(queryset[:10], many=True)

        return dict(list=serializer.data, total_count=queryset.count())


class CircleEsgView(ListVueView):
    template_name = 'esg/bbs_circle_esg_mgr.html'

    def get_pagination_list(self):
        return CircleBBSService(request=self.request, is_esg=True).get_circle_list()
