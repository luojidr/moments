"""
《Python Asyncio 并发编程》- Matthew Fowler

"""
# 以下是基本用法
import time
from datetime import datetime
from typing import Union, List
import asyncio


async def coro_add_one(num: int) -> int:
    await asyncio.sleep(1)
    return num + 1


async def main() -> Union[List[int], None]:
    results = []

    # # Cost time: 2.004997491836548
    # one_plus_one = await coro_add_one(1)
    # two_plus_one = await coro_add_one(2)

    # Cost time: 1.0022892951965332
    # await 一个task对象会更快, 多个task 也一样
    tasks = []
    for i in range(10):
        # task = asyncio.create_task(coro_add_one(i))
        task = asyncio.ensure_future(coro_add_one(i))  # 与 asyncio.create_task 一样
        tasks.append(task)

    for task in tasks[:5]:
        # ret = await asyncio.create_task(coro_add_one(i)) 与 asyncio.ensure_future(coro_add_one(i)), 此写法至少需要100s
        ret = await task
        # print(datetime.now(), task)
        results.append(ret)

    return results


start = time.time()
# rets = asyncio.run(main(), debug=False)
loop = asyncio.get_event_loop()
rets = loop.run_until_complete(main())
print(loop.__dict__)
# print([attr for attr in dir(loop) if not attr.startswith('_')])

print("Cost time:", time.time() - start)
print('rets:', len(rets), rets)

