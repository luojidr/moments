import time
from multiprocessing.dummy import Pool as ThreadPool


start_t = time.time()
pool = ThreadPool()
iterable = ("你好，%s 锤子!！!" % i for i in range(100000))
pool.map(n.rpc.greeting_service.hello, iterable)

end_t = time.time()

qps = 100000 / (end_t - start_t)