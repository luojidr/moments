import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor


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


def main():
    start = time.time()
    max_times = 1000
    iterable = list(range(max_times))

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        results = executor.map(fetch, iterable)

    ok_cnt = len(list(filter(lambda res: res == 'ok', results)))
    failed_cnt = len(list(filter(lambda res: res != 'ok', results)))

    cost_time = time.time() - start
    print(f'concurrent.ThreadPoolExecutor max_times: {max_times}, Cost: {cost_time}, '
          f'ok_cnt: {ok_cnt}, failed_cnt: {failed_cnt}')


if __name__ == '__main__':
    # concurrent.ThreadPoolExecutor max_times: 1000, Cost: 11.424465894699097, ok_cnt: 1000, failed_cnt: 0
    # 结论：concurrent.futures.ThreadPoolExecutor 耗时与 from multiprocessing.dummy.Pool 基本相当
    main()

