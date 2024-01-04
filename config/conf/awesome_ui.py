import time

SIMPLEUI_STATIC_OFFLINE = True
SIMPLEUI_HOME_INFO = False
SIMPLEUI_DEFAULT_THEME = "layui.css"

SIMPLEUI_CONFIG = {
    'system_keep': True,

    # 开启排序和过滤功能, 不填此字段为默认排序和全部显示, 空列表[] 为全部不显示.
    # 'menu_display': ['Simpleui', '测试', '权限认证', '动态菜单测试'],

    # 设置是否开启动态菜单, 默认为False. 如果开启, 则会在每次用户登陆时动态展示菜单内容
    'dynamic': True,

    'menus': [
        # {
        #     "app": "dynamic_config",
        #     "name": "动态配置",
        #     'icon': 'fas fa-cog',
        #     "url": '/dynamic/config/list',
        #     "component_name": "dynamic-config",
        # },

        # {
        #     'app': 'storage',
        #     'name': '文件存储',
        #     'icon': 'fab fa-bitbucket',
        #     'models': [
        #         {
        #             'name': '文件管理',
        #             'icon': 'fas fa-image',
        #             'url': '/storage/bucket/files/preview/list',
        #             "component_name": "bucket-files-list",
        #         },
        #
        #         {
        #             'name': 'Bucket Key',
        #             'icon': 'fas fa-key',
        #             'url': '/storage/bucket/key/list',
        #             "component_name": "bucket-key-list",
        #         },
        #
        #         {
        #             'name': '我的账户',
        #             'icon': 'fas fa-user',
        #             'url': '/storage/bucket/my/account',
        #             "component_name": "bucket-my-account",
        #         },
        #     ]
        # },

        # {
        #     'app': 'questionnaire',
        #     'name': '问卷调查',
        #     'icon': 'fab fa-bitbucket',
        #     'models': [
        #         {
        #             'name': '问卷管理',
        #             'icon': 'fas fa-image',
        #             'url': '/circle/questionnaire/manage',      # 保持与urls.py 保持一致
        #             "component_name": "survey-manage",
        #         },
        #
        #         {
        #             'name': '问卷列表',
        #             'icon': 'fas fa-key',
        #             'url': '/circle/questionnaire/list',
        #             "component_name": "survey-list",
        #         },
        #
        #         {
        #             'name': '问卷推送',
        #             'icon': 'fas fa-user',
        #             'url': '/circle/questionnaire/ding/push',
        #             "component_name": "survey-ding-push",
        #         },
        #     ]
        # },

        {
            'name': '钉钉推送',
            'icon': 'fas fa-user',
            "app": "ding_talk",
            "models": [
                {
                    'name': '媒体资源',
                    'icon': 'fas fa-film',
                    'url': '/circle/ding/message/media',
                    "component_name": "ding-message-media",
                },

                {
                    'name': '创建推送',
                    'icon': 'fas fa-user',
                    'url': '/circle/ding/message/create',
                    "component_name": "ding-message-create",
                },

                {
                    'name': '推送列表',
                    'icon': 'fas fa-comment',
                    'url': '/circle/ding/message/list',
                    "component_name": "ding-message-list",
                },

                {
                    'name': '消息撤回',
                    'icon': 'el-icon-delete-solid',
                    'url': '/circle/ding/message/recall/log',
                    "component_name": "ding-recall-log-list",
                },
            ]
        },

        {
            'name': '定时管理',
            'icon': 'fas fa-tasks',
            "app": "ding_talk",
            'models': [
                {
                    'name': '创建消息',
                    'icon': 'far fa-comment-dots',
                    'url': '/circle/ding/message/periodic/topic/add',
                    "component_name": "ding-periodic-topic-add",
                },

                {
                    'name': ' 添加任务',
                    'icon': 'el-icon-circle-plus',
                    'url': '/circle/ding/message/periodic/task/add',
                    "component_name": "ding-periodic-task-add",
                },

                {
                    'name': '管理任务',
                    'icon': 'far fa-chart-bar',
                    'url': '/circle/ding/message/periodic/task/list',
                    "component_name": "ding-periodic-task-list",
                },
            ],
        },

        {
            'name': '图片管理',
            'icon': 'fas fa-camera-retro',
            "app": "aliyun",
            'models': [
                {
                    'name': '上传图片',
                    'icon': 'fas fa-upload',
                    'url': '/circle/aliyun/static-file/upload',
                    "component_name": "image-upload-list",
                },
            ],
        },

        {
            "app": "monitor",
            "name": "任务监控",
            'icon': 'fas fa-spider',
            "url": '/circle/monitor/celery/flower',
            "component_name": "monitor-flower",
        },

    ]
}

T_SITE_TITLE = "星圈管理后台"
T_SITE_HEADER = "星圈管理后台"
