from datetime import datetime
import asyncio,random

# 异步中不允许单独使用：yield
# 注意："@asyncio.coroutine" decorator is deprecated since Python 3.8, use "async def" instead


@asyncio.coroutine
def smart_fib(n):
    index = 0
    a = 0
    b = 1
    while index < n:
        sleep_secs = random.uniform(1, 3)
        print("Entry Index: %s, Now: %s" % (index, datetime.now()))

        # 说明：相当于执行 await asyncio.sleep(sleep_secs) , 此时程序在此暂停，控制权交给事件循环
        yield from asyncio.sleep(sleep_secs)  # 通常yield from后都是接的耗时操作
        print('      Index: {}, Now: {} Smart one think {} secs to get {} '.format(index, datetime.now(), sleep_secs, b))
        a, b = b, a + b
        index += 1


async def mygen(alist):
    while len(alist) > 0:
        c = random.randint(0, len(alist) - 1)
        val = alist.pop(c)
        print("Now: %s mygen will pop: %s" % (datetime.now(), val))
        await asyncio.sleep(1)
        print("Now: %s mygen ok: %s" % (datetime.now(), val))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    # tasks = [
    #     smart_fib(10),
    #     # stupid_fib(10),
    # ]

    tasks = [
        mygen(["ss", "dd", "gg"]),
        mygen([1, 2, 3, 4, 5])
    ]

    loop.run_until_complete(asyncio.wait(tasks))
    print('All fib finished.')
    loop.close()
