from elasticsearch import Elasticsearch

client = Elasticsearch(
    hosts=['127.0.0.1:9200'],
    http_auth=('elastic', '123456')
)
print(client.ping())
