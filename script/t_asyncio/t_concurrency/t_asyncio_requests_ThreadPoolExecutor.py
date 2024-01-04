import os
import time
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor

max_times = 1000


def fetch(i):
    # 使用 requests 同步抓取
    headers = {"Content-Type": "application/json"}
    api = 'https://api-circle.fosun.com/circle/health/check'

    try:
        r = requests.get(api, headers=headers)

        if r.status_code == 200:
            data = r.json()

            if data.get('code') == 200:
                return 'ok'
    except Exception as e:
        pass

    return 'failed'


async def run_tasks(executor):
    loop = asyncio.get_event_loop()

    blocking_tasks = []

    for i in range(max_times):
        task = loop.run_in_executor(executor, fetch, i)
        task.__num = i

        blocking_tasks.append(task)

    completed, pending = await asyncio.wait(blocking_tasks)
    results = {t.__num: t.result() for t in completed}

    return results


def main():
    start = time.time()

    event_loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=os.cpu_count())

    # results: {0: 'ok', 4: 'ok', 1: 'ok', 5: 'ok', 2: 'ok', 3: 'ok'}
    results = event_loop.run_until_complete(run_tasks(executor))

    ok_cnt = len([v for v in results.values() if v == 'ok'])
    failed_cnt = len([v for v in results.values() if v != 'ok'])

    cost_time = time.time() - start
    print(f'asyncio+concurrent.ThreadPoolExecutor max_times: {max_times}, Cost: {cost_time}, '
          f'ok_cnt: {ok_cnt}, failed_cnt: {failed_cnt}')


if __name__ == '__main__':
    # asyncio+requests+concurrent.ThreadPoolExecutor max_times: 1000, Cost: 11.705099821090698, ok_cnt: 1000, failed_cnt: 0
    # 结论：与concurrent.futures.ThreadPoolExecutor 耗时相当，但是比同步写法稍复杂，但性能没有提升
    main()

