import re
import json

from werobot import WeRoBot
from werobot.replies import ArticlesReply, Article

from config.conf.werobot import WeRobotConfig
from fosun_circle.libs.log import dj_logger

robot = WeRoBot(
    enable_session=False,
    logger=dj_logger,
    config=WeRobotConfig.get_config()
)

client = robot.client
# client.create_menu(WeRobotConfig.MENU_ITEMS)  # 个人主体没有权限创建


@robot.handler
def hello(message, session):
    robot.logger.info("robot.handler => message: %s, session:%s", message, session)
    return "上海天气\n" \
           "    天气：晴转多云\n" \
           "    温度：15-20℃\n" \
           "    空气：优\n" \
           "           \n" \
           "    主要污染物\n" \
           "       PM2.5：优  SO2：优  O3：优\n" \
           "       PM10 ：优  NO2：优  CO：-\n"


# @robot.text
# def handle_text(message, session):
#     robot.logger.info("robot.text => message: %s, session:%s", message, session)
#     return "处理文本，请稍后......"


@robot.image
def handle_image(message, session):
    robot.logger.info("robot.image => message: %s, session:%s", message, session)
    return "处理图片，请稍后......"


@robot.key_click(key="V1001_TODAY_MUSIC")
def handle_menu_songs(message, session):
    robot.logger.info("robot.key_click(key='V1001_TODAY_MUSIC') => message: %s, session:%s", message, session)
    return "今日没有新歌，明天再来吧......"


@robot.filter(re.compile(r".*ip|IP|host|HOST.*"))
def handle_domain_ip(message, session, match):
    robot.logger.info("robot.filter ip => message: %s, session:%s, match:%s", message, session, match)
    return json.dumps(client.get_ip_list(), indent=4)


@robot.filter(re.compile(r".*管理|离职|辞职.*"))
def blog(message, session, match):
    robot.logger.info("robot.filter[blog]  => message: %s, session:%s, match:%s", message, session, match)

    reply = ArticlesReply(message=message)
    # article = Article(
    #     title="管理-两个实打实干活的同事离职了，老板连谈都没谈，一句挽留都没有，你怎么看？",  # 标题
    #     description="可是你不听啊，你每天就关注组织结构啊、目标啊、流程啊、绩效考核啊、晋升啊这些东西，这些都是纸上的制度，它适用于大多数人，但是对于重点人物，你还得有其他手段。你就得厚黑，懂吗，什么科学管理，科学能管人性吗？不能！人性只能用手段去较劲。",  # 简介
    #     img="https://picx.zhimg.com/80/v2-bfdeed9f2bda87da4a0ccd863da91b46_1440w.jpg?source=1940ef5c",  # 图片链接
    #     url="https://www.zhihu.com/answer/2608283622"  # 点击图片后跳转链接
    # )

    article = Article(
        title="上海天气？",  # 标题
        description="上海天气\n" \
           "    天气：晴转多云\n" \
           "    温度：15-20℃\n" \
           "    空气：优\n" \
           "           \n" \
           "    主要污染物\n" \
           "       PM2.5：优  SO2：优  O3：优\n" \
           "       PM10 ：优  NO2：优  CO：-\n",
        # 简介
        img="https://picx.zhimg.com/80/v2-bfdeed9f2bda87da4a0ccd863da91b46_1440w.jpg?source=1940ef5c",  # 图片链接
        url="https://tianqi.2345.com/shanghai1d/58362.htm"  # 点击图片后跳转链接
    )
    reply.add_article(article)

    # article2 = Article(
    #     title="上班中哪一个瞬间让你觉得应该辞职了？",  # 标题
    #     description="老板儿子突然给我转来200000元，然后打来电话说：你能在3个月内把我们公司搞关门吗？如果能办到，我再给你20万。我是做运营的，每天花钱如流水，每年手里出去的钱上千万，所以这20万并不是什么大数字，可是，他给我20万，是让我把他们公司搞关门，这太匪夷所思了。",
    #     img="https://pica.zhimg.com/v2-e82c44afd4dbe8500fadb170862a8631_1440w.jpg?source=172ae18b",  # 图片链接
    #     url="https://zhuanlan.zhihu.com/p/553737487"  # 点击图片后跳转链接
    # )
    # reply.add_article(article2)

    return reply

