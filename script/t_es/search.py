import json

from elasticsearch_dsl import Search

from script.t_es import client


# 方式一
response = client.search(
    index="student",
    query={
        "bool": {
            "must": {"match": {"about": "travel"}},
            "filter": [{"term":{"age": 20}}]
        }
    },
)

print(json.dumps(response, indent=4, ensure_ascii=False))

# 方式二
res = Search(using=client, index="student")\
    .filter("match", about="travel")\
    .execute()
print(res)
print(type(res))
print(dir(res))

for k in res:
    print(k)
    print(dir(k))
    print(k.meta.__dict__)
