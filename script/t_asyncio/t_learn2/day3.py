"""
https://iswbm.com/121.html

1: 多线程的基本使用
2: Queue消息队列的使用
3: Redis的基本使用
4: asyncio的使用

如何将协程态添加到事件循环中的???
"""

import time
import redis
import asyncio
from queue import Queue as SyncQueue
from asyncio.queues import Queue as AsyncQueue
import threading


def start_loop(loop):
    # 一个在后台永远运行的事件循环
    asyncio.set_event_loop(loop)
    loop.run_forever()


def do_sleep_sync(x, q, msg=""):
    time.sleep(x)
    q.put(msg)


async def do_sleep_async(x, q, msg=""):
    await asyncio.sleep(x)  # 一定不能使用time.sleep(x)
    q.put(msg)


def main_thread_sync_to_dynamic_tasks():
    """ 主线程是同步的 """
    queue = SyncQueue()  # 普通队列
    new_loop = asyncio.new_event_loop()

    # 定义一个线程，并传入一个事件循环对象
    t = threading.Thread(target=start_loop, args=(new_loop,))
    t.start()
    print(time.ctime())

    # 动态添加两个协程
    # 这种方法，在主线程是【同步】的
    new_loop.call_soon_threadsafe(do_sleep_sync, 6, queue, "第一个")
    new_loop.call_soon_threadsafe(do_sleep_sync, 3, queue, "第二个")

    while True:
        msg = queue.get()
        print("{} 协程运行完..".format(msg))
        print(time.ctime())

    # 由于是同步的，所以总共耗时6+3=9秒


def main_thread_async_to_dynamic_tasks():
    """ 主线程是异步的，这是重点，一定要掌握 """
    queue = SyncQueue()  # 普通队列
    new_loop = asyncio.new_event_loop()

    # 定义一个线程，并传入一个事件循环对象
    t = threading.Thread(target=start_loop, args=(new_loop,))
    t.start()
    print(time.ctime())

    # 动态添加两个协程
    # 这种方法，在主线程是【异步】的
    asyncio.run_coroutine_threadsafe(do_sleep_async(6, queue, "第一个"), new_loop)
    asyncio.run_coroutine_threadsafe(do_sleep_async(3, queue, "第二个"), new_loop)

    while True:
        msg = queue.get()  # 如果用异步队列，必须是 await queue.get(),那么main_thread_async也必须是协程函数才行
        print("{} 协程运行完..".format(msg))
        print(time.ctime())

    # 由于是异步的，所以总共耗时6秒


def redis_main_thread_async_to_dynamic_tasks():
    """ 利用redis实现动态添加任务 """
    def get_redis():
        # 最好使用异步redis包， 这里是用redis模拟动态添加任务，简单化了
        connection_pool = redis.ConnectionPool(host='127.0.0.1', db=0)
        return redis.Redis(connection_pool=connection_pool)

    def consumer():
        while 1:
            task = redis_conn.rpop('rds_queue')
            if not task:
                time.sleep(1)
                continue

            asyncio.run_coroutine_threadsafe(do_sleep_async(int(task), queue, "ok"), new_loop)

    print(time.ctime())
    redis_conn = get_redis()
    queue = SyncQueue()  # 普通队列
    new_loop = asyncio.new_event_loop()

    # 定义一个线程，运行一个事件循环对象，用于实时接收新任务
    loop_thread = threading.Thread(target=start_loop, args=(new_loop,))
    loop_thread.setDaemon(True)
    loop_thread.start()

    # 子线程：用于消费队列消息，并实时往事件对象容器中添加新任务
    consumer_thread = threading.Thread(target=consumer)
    consumer_thread.setDaemon(True)
    consumer_thread.start()

    while True:
        msg = queue.get()  # 队列get阻塞，否则直接刷屏了
        print("协程运行完..")
        print("当前时间：", time.ctime())


if __name__ == '__main__':
    # main_thread_sync_to_dynamic_tasks()
    # main_thread_async_to_dynamic_tasks()
    redis_main_thread_async_to_dynamic_tasks()
