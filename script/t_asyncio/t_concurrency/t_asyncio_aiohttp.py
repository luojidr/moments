import asyncio
import time
import aiohttp
import traceback

max_times = 1000


async def fetch(i):
    # 使用 aiohttp 异步抓取
    headers = {"Content-Type": "application/json"}
    api = 'https://api-circle.fosun.com/circle/health/check'

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api, headers=headers) as r:
                if r.status == 200:
                    data = await r.json()

                    if data.get('code') == 200:
                        return 'ok'
    except Exception as e:
        pass

    return 'failed'


async def scrape(session=None):
    """
    async with aiohttp.ClientSession() as session:
        async with session.get('http://httpbin.org/get') as resp:
            print(resp.status)
            print(await resp.text())
            print(await resp.json())
    """
    headers = {"Content-Type": "application/json"}
    base_url = 'https://api-circle.fosun.com'
    api_path = '/circle/health/check'

    is_tmp = False

    try:
        if session is None:
            is_tmp = True
            session = aiohttp.ClientSession()

        async with session.get(base_url + api_path, headers=headers) as r:
            if r.status == 200:
                data = await r.json()

                if data.get('code') == 200:
                    return 'ok'
    except Exception as e:
        print(traceback.format_exc())
    finally:
        if is_tmp:
            await session.close()

    return 'failed'


def main():
    start = time.time()

    event_loop = asyncio.get_event_loop()
    tasks = [fetch(i) for i in range(max_times)]
    results = event_loop.run_until_complete(asyncio.gather(*tasks))

    # session = aiohttp.ClientSession()  # 不建议这么使用
    # tasks = [scrape(session) for i in range(max_times)]
    # results = event_loop.run_until_complete(asyncio.gather(*tasks))
    # session.close()  # 不建议这么使用

    ok_cnt = len([v for v in results if v == 'ok'])
    failed_cnt = len([v for v in results if v != 'ok'])

    cost_time = time.time() - start
    print(f'asyncio+aiohttp max_times: {max_times}, Cost: {cost_time}, ok_cnt: {ok_cnt}, failed_cnt: {failed_cnt}')


if __name__ == '__main__':
    # asyncio+aiohttp max_times: 1000, Cost: 5.343931674957275, ok_cnt: 1000, failed_cnt: 0
    # 结论：正统 => asyncio+aiohttp 耗时很短，性能提升很大，比 asyncio+requests+ThreadPoolExecutor 这种异步混同步的效果要好很多
    main()

