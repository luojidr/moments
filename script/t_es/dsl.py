import json
import random
from datetime import datetime

from faker import Faker

from elasticsearch import Elasticsearch
from elasticsearch_dsl.query import MultiMatch
from elasticsearch_dsl import connections, Search
from elasticsearch_dsl import Q, A, Document, Date, Integer, Keyword, Text

# 官方文档： https://elasticsearch-dsl.readthedocs.io/en/latest/configuration.html

# 创建连接
connections.create_connection(hosts=['localhost:9200'], http_auth=('elastic', '123456'), timeout=20)

# configure定义多个指向不同集群的连接（好像补鞥呢单独使用）
# connections.configure(
#     default={'hosts': 'localhost'},
#     dev={'hosts': ['localhost:9200'], 'sniff_on_start': True},
# )

# 重要难点
# 1) analyzer 分词器
#   http://www.ay1.cc/article/10106.html
#   https://blog.csdn.net/weixin_43452424/article/details/110939869
#   https://www.cnblogs.com/gmhappy/p/9472377.html


class Article(Document):
    title = Text(analyzer='snowball', fields={'raw': Keyword()})  # 雪球分析器
    body = Text(analyzer='snowball')
    tags = Keyword()
    published_from = Date()
    lines = Integer()

    class Index:
        name = "blog"
        settings = {
            "number_of_replicas": 2
        }

    def save(self, **kwargs):
        self.lines = len(self.body.split())
        return super().save(**kwargs)

    def is_published(self):
        return datetime.now() >= self.published_from


# create the mappings in elasticsearch
Article.init()

fk = Faker(['zh_CN'])

is_created = True
# 1) CURD 创建索引
# 创建100个
if not is_created:
    for i in range(100):
        title = fk.paragraph()
        body = fk.text()
        tags = fk.words(nb=random.randint(2, 8))
        published_from = fk.date()

        article = Article(
            meta={"id": i + 1},
            title=title, body=body,
            tags=tags, published_from=published_from
        )
        article.save()

# 2) CURD 查询
#   2.1) 查询单个
article = Article.get(id=1)  # 如果不存在, Raise elasticsearch.exceptions.NotFoundError
print("One Query:", article, article.title)

#   2.2) 查询多个
articles = Article.mget([1, 2, 3])
article_list = Article.mget(docs=[{"_id": 10}, {"_id": 11}, {"_id": 12}])
print("Multi Query:", articles)
print("Multi Query List:", article_list)


# 3) CURD 更新(只有单个更新)
#   3.1) 单个更新
article = Article.get(id=1)
print("Update Origin tags: ", article.tags, article.title)
article.tags = fk.words(nb=random.randint(2, 8))
print("Update After tags: ", article.tags)
article.save()
# 或者
article.update(published_by=datetime.now())

# 4) CURD 删除(只有单个删除)
article = Article.get(id=100)
# article.delete()

# DSL操作
client = Elasticsearch(hosts=['127.0.0.1:9200'], http_auth=('elastic', '123456'))
es = Search(using=client)  # 偏底层的操作

# 5) 查询(queries)
#    5.1) 创建一个查询语句
s = Search().using(client).query("match", title="文章图片活动电影上海一种")
print("ES Rest Query Param:", s.to_dict())  # to_dict: 查看查询语句对应的字典结构(就是ES Rest查询的参数格式)
# 发送查询请求到Elasticsearch
response = s.execute()
# 打印查询结果
for hit in s:
    print(str(hit.meta.id) + " queries:", hit.title)
# 删除查询
# s.delete()

#    5.2) 创建一个多字段查询
multi_match = MultiMatch(query='上海', fields=['title', 'body'])
s = Search().query(multi_match)
print(s.to_dict())  # Rest查询的参数格式
# 使用Q语句
q = Q({'multi_match': {"query": "管理", "fields": ["title", "tags"]}})
s = Search().query(q)
print("multi_match Q:", s.to_dict())
# If you already have a query object, or a dict representing one,
# you can just override the query used in the Search object:
s.query = Q('bool', must=[Q('match', title='上海'), Q('match', body='管理')])
print(s.to_dict())
print(json.dumps(s.to_dict(), ensure_ascii=False))
# print("Bool Query:", s.execute())
# 查询组合
q = Q("match", title='python') | Q("match", title='django')  # Or
s = Search().query(q)
print("查询组合 OR: ", s.to_dict())
q = Q("match", title='python') & Q("match", title='django')
s = Search().query(q)
print("查询组合 AND:", s.to_dict())
q = ~Q("match", title="python")
s = Search().query(q)
print("查询组合 NOT:", s.to_dict())

# 6) Filters
sf = Search()
sf1 = sf.filter("terms", tags=['部门',  "女人"])  # tags中包含任何一个过滤词的都过滤出来
print("Filter [terms] Query:", json.dumps(sf1.to_dict(), ensure_ascii=False))
sf2 = sf.query('bool', filter=[Q('terms', tags=['部门', '女人'])])
print("Filter [bool] Query :", json.dumps(sf2.to_dict(), ensure_ascii=False))
ret = sf.exclude('terms', tags=['部门', '女人'])
# print(list(ret))
sf3 = sf.query('bool', filter=[~Q('terms', tags=['search', 'python'])])
print("Filter [NOT] Query :", json.dumps(sf3.to_dict(), ensure_ascii=False))

# 7) Aggregations(好像有点不咋，未执行通过)
sa = Search()
aa = A('terms', field='tags')
sa.aggs.bucket('title_terms', aa)
print("Aggregations Query :", json.dumps(sa.to_dict(), ensure_ascii=False))
print("Aggregations Ret:", sa.execute())

# 7) Sorting
ss = Search().sort(
    '-published_from',
    {"lines": {"order": "asc", "mode": "avg"}}
)
print("Sorting Query :", json.dumps(ss.to_dict(), ensure_ascii=False))

# 8) Pagination
sss = Search()
sss = sss[10:20]
print("Sorting Query :", json.dumps(sss.to_dict(), ensure_ascii=False))

# 9) Extra Properties and parameters
pass




