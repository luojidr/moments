"""
XXExecutor 其实就是封装了队列，但是由于 run_in_executor 并不能传入【异步函数】，我们不能按照例子 2 来用。
独立使用队列其实效果应该和 ThreadPoolExecutor 差不多，那我们可不可以把任务平均切分一下，尽量让每个线程拿到的任务差不多
"""
import math
import os
import time
import aiohttp
import asyncio
from itertools import chain
from concurrent.futures import ThreadPoolExecutor

max_times = 1000
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# LOOP = asyncio.new_event_loop()
# asyncio.set_event_loop(LOOP)


async def fetch(i):
    # 使用 aiohttp 异步抓取
    headers = {"Content-Type": "application/json"}
    api = 'https://api-circle.fosun.com/circle/health/check'

    try:
        async with aiohttp.request("GET", api) as r:
            if r.status == 200:
                data = await r.json()

                if data.get('code') == 200:
                    return 'ok'
    except Exception as e:
        pass

    return 'failed'


def run_one_task():
    """ 单个执行 """
    # loop.run_in_executor 不能传入异步的函数
    LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(LOOP)

    coro = fetch(1)
    result = LOOP.run_until_complete(coro)

    # result = asyncio.run(fetch(1))
    return result


def run_chunk_tasks(times):
    """ 批量执行 """
    # loop.run_in_executor 不能传入异步的函数
    LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(LOOP)

    coro_list = [fetch(i) for i in range(times)]
    result = LOOP.run_until_complete(asyncio.gather(*coro_list))

    return result


async def run(executor, times=None):
    loop = asyncio.get_event_loop()

    if times is not None:
        # 分批执行
        blocking_task = loop.run_in_executor(executor, run_chunk_tasks, times)
    else:
        # 单个执行
        blocking_task = loop.run_in_executor(executor, run_one_task)

    completed, pending = await asyncio.wait([blocking_task])
    results = [t.result() for t in completed]

    return results


def main():
    start = time.time()

    cpu_count = os.cpu_count()
    event_loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=cpu_count)

    # results: {0: 'ok', 4: 'ok', 1: 'ok', 5: 'ok', 2: 'ok', 3: 'ok'}
    # 单个执行
    # coro_list = [run(executor, None) for i in range(max_times)]
    # results = event_loop.run_until_complete(asyncio.gather(*coro_list))
    # results = list(chain.from_iterable(results))
    # print(results)

    # 分批执行
    chunk_size = math.ceil(max_times // cpu_count)
    coro_list = [run(executor, chunk_size) for i in range(cpu_count)]
    results = event_loop.run_until_complete(asyncio.gather(*coro_list))
    results = list(chain.from_iterable(results))
    results = list(chain.from_iterable(results))
    print(results)

    ok_cnt = len([v for v in results if v == 'ok'])
    failed_cnt = len([v for v in results if v != 'ok'])

    cost_time = time.time() - start
    print(f'asyncio+aiohttp+ThreadPoolExecutor 单个执行 max_times: {max_times}, Cost: {cost_time}, '
          f'ok_cnt: {ok_cnt}, failed_cnt: {failed_cnt}')


if __name__ == '__main__':
    # 单个执行
    # asyncio+aiohttp+ThreadPoolExecutor 单个执行 max_times: 1000, Cost: 10.495088815689087, ok_cnt: 1000, failed_cnt: 0
    # 结论：
    #   1) 与asyncio+requests+concurrent.ThreadPoolExecutor 耗时相当，但是比写法比同异步混合写更加复杂，性能没有提升
    #   2) 与concurrent.ThreadPoolExecutor 耗时相当

    # 分批执行
    # asyncio+aiohttp+ThreadPoolExecutor 单个执行 max_times: 1000, Cost: 6.474109649658203, ok_cnt: 1000, failed_cnt: 0
    # 结论：依然比 asyncio+aiohttp 慢了一丢丢， 但是比【单个执行】 要快的多，写法比其他几种也比较复杂
    #      所以， 还是用 asyncio+aiohttp 吧，正统
    #      所以， 还是用 asyncio+aiohttp 吧，正统
    main()

