from django.apps import apps
from django.db.models import Q
from django.db import connection
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from rest_framework import mixins, views
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, GenericAPIView

from fosun_circle.libs import exception
from fosun_circle.contrib.drf.throttling import ApiClientRateThrottle
from fosun_circle.core.views import ListVueView, SingleVueView
from .serializers import MenuSerializer, GroupSerializer, ApiInvokerClientSerializer, ApiInvokerUrlSerializer
from .models import MenuModel, OwnerToMenuPermissionModel, GroupOwnedMenuModel, ApiInvokerClientModel

UserModel = get_user_model()


class GroupView(ListVueView):
    template_name = "permissions/group_list.html"
    serializer_class = GroupSerializer

    def get_pagination_list(self):
        queryset = self.serializer_class.Meta.model.objects.filter(is_del=False)
        serializer = self.serializer_class(queryset[:10], many=True)
        return dict(list=serializer.data, total_count=queryset.count())


class MenuView(SingleVueView):
    template_name = "permissions/menu_list.html"


class ListGroupApi(ListAPIView):
    serializer_class = GroupSerializer

    def get_queryset(self):
        name = self.request.query_params.get('name')
        base_queryset = self.serializer_class.Meta.model.objects.all()

        group_q = Q()
        group_q.connector = 'OR'

        if name:
            group_q.children.append(('name__icontains', name))

            group_ids = OwnerToMenuPermissionModel.objects\
                .filter(user__username__icontains=name, is_del=False)\
                .values_list('group_id', flat=True)

            menu_ids = GroupOwnedMenuModel.objects\
                .filter(menu__name__icontains=name, is_del=False)\
                .values_list('group_id', flat=True)

            group_q.children.append(('id__in', list(set(group_ids) | set(menu_ids))))

        queryset = base_queryset.filter(group_q, is_del=False).all()
        return queryset


class ListMenuApi(ListAPIView):
    serializer_class = MenuSerializer

    def get_queryset(self):
        key = self.request.query_params.get('key')
        Model = self.serializer_class.Meta.model
        fields = Model.fields()

        if key:
            recursive_kwargs = dict(
                key=key, menu_table=Model._meta.db_table,
                menu_fields=', '.join(fields),
                parent_menu_fields=', '.join(['parent.%s' % f for f in fields]),
            )

            # recursive query
            sql = """
                WITH RECURSIVE recursive_tree AS 
                (
                    SELECT {menu_fields} FROM {menu_table} 
                    WHERE (name like '%{key}%' or url like '%{key}%') and is_del=false
                    UNION 
                    SELECT {parent_menu_fields} FROM {menu_table} parent
                    INNER JOIN recursive_tree child
                    ON child.parent_id = parent.id 
                    WHERE parent.is_del=false
                )
                SELECT {menu_fields} FROM recursive_tree 
                ORDER BY parent_id, level, menu_order
            """
            cursor = connection.cursor()
            cursor.execute(sql.format(**recursive_kwargs))
            db_menu_tree_rets = cursor.fetchall()

            queryset = [Model(**dict(zip(fields, items))) for items in db_menu_tree_rets]
        else:
            queryset = Model.objects.filter(is_del=False).all()

        return queryset


class OperateGroupApi(mixins.CreateModelMixin,
                      mixins.UpdateModelMixin,
                      GenericAPIView):
    serializer_class = GroupSerializer

    def get_object(self):
        pk = self.request.data.get('id') or 0
        return self.serializer_class.Meta.model.objects.get(id=pk)

    def post(self, request, *args, **kwargs):
        if not request.data.get('id'):
            return self.create(request, *args, **kwargs)

        if request.data.get('action') == 'delete':
            instance = self.get_object()
            instance.save_attributes(force_update=True, is_del=True)
            return Response()

        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class ListInvokerClientApi(ListAPIView):
    serializer_class = ApiInvokerClientSerializer

    def get_queryset(self):
        request = getattr(self, 'request', None)
        query_params = getattr(request, 'query_params', {})

        query = dict(is_del=False)
        name = query_params.get('name')
        client_id = query_params.get('client_id')
        access_token = query_params.get('access_token')

        name and query.update(name__icontains=name)
        client_id and query.update(access_token=access_token)
        access_token and query.update(access_token__icontains=access_token)

        key = query_params.get('key')
        is_option = query_params.get('is_option') == 'true'

        if key:
            query.update(name__icontains=name)

        queryset = self.serializer_class.Meta.model.objects.filter(**query).all()
        return queryset.values('id', 'name') if is_option else queryset


class OperateInvokerClientApi(mixins.CreateModelMixin,
                              mixins.UpdateModelMixin,
                              GenericAPIView):
    serializer_class = ApiInvokerClientSerializer

    def get_object(self):
        pk = self.request.data.get('id')
        return self.serializer_class.Meta.model.objects.get(id=pk)

    def post(self, request, *args, **kwargs):
        """ Create, Update, Delete """
        action = request.data.pop('action', None)
        assert action in ['create', 'update', 'delete'], 'Operate API Client Action Error!'

        if action == 'create':
            name, remark = request.data['name'], request.data['remark']
            invoker_data = self.serializer_class.Meta.model.create_invoker_client(name, remark)

            return Response(invoker_data)

        if action == 'delete':
            instance = self.get_object()
            instance.is_del = True
            instance.save()
            return Response()

        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class ApiInvokerClientView(ListVueView):
    template_name = "permissions/api_invoker_client.html"

    def get_pagination_list(self):
        queryset = ListInvokerClientApi().get_queryset()
        serializer = ListInvokerClientApi.serializer_class(queryset[:10], many=True)
        return dict(list=serializer.data, total_count=queryset.count())


class ListInvokerUrlApi(ListAPIView):
    serializer_class = ApiInvokerUrlSerializer

    def get_queryset(self):
        request = getattr(self, 'request', None)
        query_params = getattr(request, 'query_params', {})

        query = dict(is_del=False)
        api_path = query_params.get('url')
        api_name = query_params.get('name')
        invoker_id = query_params.get('invoker_id')

        api_path and query.update(url__icontains=api_path)
        api_name and query.update(name__icontains=api_name)
        invoker_id and query.update(invoker_id=invoker_id)

        return self.serializer_class.Meta.model.objects.filter(**query).prefetch_related('invoker')


class OperateInvokerPathApi(mixins.CreateModelMixin,
                            mixins.UpdateModelMixin,
                            GenericAPIView):
    serializer_class = ApiInvokerUrlSerializer

    def get_object(self):
        pk = self.request.data.get('id')
        return self.serializer_class.Meta.model.objects.get(id=pk)

    def post(self, request, *args, **kwargs):
        """ Create, Update, Delete """
        action = request.data.pop('action', None)
        assert action in ['create', 'update', 'delete'], 'Operate API Url Action Error!'

        if action == 'create':
            return self.create(request, *args, **kwargs)

        if action == 'delete':
            instance = self.get_object()
            instance.is_del = True
            instance.save()
            return Response()

        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class ApiInvokerPathView(ListVueView):
    template_name = "permissions/api_invoker_path.html"

    def get_pagination_list(self):
        queryset = ListInvokerUrlApi().get_queryset()
        serializer = ListInvokerUrlApi.serializer_class(queryset[:10], many=True)
        return dict(list=serializer.data, total_count=queryset.count())


class AccessTokenInvokerClientApi(views.APIView):
    throttle_classes = (ApiClientRateThrottle, )

    def get(self, request, *args, **kwargs):
        """
        在使用access_token时，请注意：
        1) access_token有效期为3600秒，有效期内重复获取会返回相同结果并自动续期，过期后获取会返回新的access_token
        2) 不能频繁调用gettoken接口，否则会受到频率拦截。

        """
        app_key = request.query_params.get('app_key')
        app_secret = request.query_params.get('app_secret')
        data = dict(access_token=None, expires_in=0)

        try:
            invoker_obj = ApiInvokerClientModel.objects.get(
                is_del=False,
                app_key=app_key, app_secret=app_secret
            )
        except ObjectDoesNotExist:
            raise exception.InvalidTokenError('非法的app_key和app_secret，请联系管理员！')
        except MultipleObjectsReturned:
            raise exception.InvalidTokenError('app_key和app_secret存在多个客户，请联系管理员！')
        else:
            invoker_obj.set_token()
            data.update(access_token=invoker_obj.access_token, expires_in=invoker_obj.DEFAULT_EXPIRE_IN)

        return Response(data=data)


class MenuTreeApi(views.APIView):
    def get(self, request, *args, **kwargs):
        is_leaf = request.query_params.get('is_leaf')
        return Response(data=MenuModel.get_menu_tree(is_leaf=is_leaf in [None, '1', 'true']))


class MenuAppSelectApi(views.APIView):
    def get(self, request, *args, **kwargs):
        _apps = []
        apps_path = str(settings.PROJECT_DIR)
        django_apps = apps.app_configs

        for app in django_apps.values():
            module = app.module
            module_path = module.__path__[0]

            if module_path.startswith(apps_path):
                _apps.append(app.name)

        return Response(dict(apps=[dict(id=i, name=_apps[i]) for i in range(len(_apps))]))


class MenuOrderSelectApi(views.APIView):
    def get(self, request, *args, **kwargs):
        menu_id = request.query_params.get('menu_id')
        parent_id = request.query_params.get('parent_id')
        queryset = MenuModel.objects.filter(parent_id=parent_id, is_del=False).all()

        if queryset.count() == 0:
            queryset = MenuModel.objects.filter(id=parent_id, is_del=False).all()

        queryset = queryset.exclude(id=menu_id)
        return Response(dict(menu_orders=queryset.values('id', 'name')))


class OperateMenuApi(mixins.CreateModelMixin,
                     mixins.UpdateModelMixin,
                     GenericAPIView):
    serializer_class = MenuSerializer

    def get_object(self):
        pk = self.request.data.get('id') or 0
        return self.serializer_class.Meta.model.objects.get(id=pk)

    def post(self, request, *args, **kwargs):
        action = request.data.pop('action', None)

        if action == 'delete':
            instance = self.get_object()
            instance.save_attributes(force_update=True, is_del=True)
            return Response()

        kwargs['partial'] = True
        dispatch_meth = getattr(self, action)
        return dispatch_meth(request, *args, **kwargs)


