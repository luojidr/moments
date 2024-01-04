import os
import time
import requests
from multiprocessing.dummy import Pool as ThreadPool


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
    pool = ThreadPool(processes=os.cpu_count())
    iterable = list(range(max_times))
    results = pool.map(fetch, iterable=iterable)
    pool.close()
    pool.join()

    ok_cnt = len(list(filter(lambda res: res == 'ok', results)))
    failed_cnt = len(list(filter(lambda res: res != 'ok', results)))

    cost_time = time.time() - start
    print(f'Multiprocessing.ThreadPool max_times: {max_times}, Cost: {cost_time}, '
          f'ok_cnt: {ok_cnt}, failed_cnt: {failed_cnt}')


if __name__ == '__main__':
    # Multiprocessing.ThreadPool max_times: 1000, Cost: 12.552887678146362, ok_cnt: 1000, failed_cnt: 0
    main()
