import asyncio
from typing import List, Set, Coroutine
import aiohttp
from aiohttp import ClientSession
from t4_async_timed import async_timed


# @async_timed()
async def fetch_status(session: ClientSession, url: str, delay: int) -> int:
    await asyncio.sleep(delay)

    async with session.get(url) as resp:
        return resp.status


@async_timed()
async def main():
    # 默认 ClientSession 将创建最多100个连接
    async with aiohttp.ClientSession() as session:
        url = 'https://circle.fosun.com/api/v1/circle/common/health/check'
        coro_list: List[Coroutine] = [fetch_status(session, url, i) for i in range(10)]

        # as_completed: async_timed -> finished <function main at 0x0000021C40143E50> in 9.0512 second(s)
        #   timeout: 任务超时后，未执行完的任务都不会再执行
        for finished_task in asyncio.as_completed(coro_list, timeout=4):
            try:
                ret = await finished_task  # 某一任务执行结束就会立刻返回，而不是像 gather 那样等待所有的任务都结束才返回
                print(f'Asyncio as_completed name: {finished_task.__name__} ret: {ret}')
            except asyncio.TimeoutError:
                print(f'We got a timeout task: {finished_task}')

        for task in asyncio.all_tasks():
            print(task.get_name())


if __name__ == '__main__':
    # Fix to raise RuntimeError('Event loop is closed')
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(), debug=True)


