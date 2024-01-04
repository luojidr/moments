"""
RuntimeError: Session is closed:
    原因：asyncio.wait 中 timeout 参数，对于任务集合中超过了这个时间，wait 会返回已经执行完的任务和仍在运行的任务，
         如果不对这些运行的任务进行处理，那么 async with aiohttp.ClientSession() as session 退出的时候会自动关闭，
         导那些还在时间循环里的正在运行的任务会丢失 session，Raise RuntimeError("Session is closed")

wait parameters:
    timeout: 执行任务集合的超时时间(秒)，超过了这个时间，wait 就会返回结果
    return_when:
"""
import asyncio
from typing import List, Set, Coroutine
import aiohttp
from aiohttp import ClientSession
from aiohttp_socks import ProxyConnector
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

        # pending: 仍在运行的任务
        done, pending = await asyncio.wait(coro_list, timeout=4)
        print(f'asyncio.wait done len: {len(done)}')
        for done_task in done:
            # ret = await done_task  # 不需要 await 挂起任务（让任务执行IO操作），因为任务已经执行完成了
            print(f'Done task name: {done_task.get_name()}, Ret: {done_task.result()}')

        print(f'asyncio.wait pending len: {len(pending)}')
        for pending_task in pending:
            # ret = await done_task
            print(f'Pending task name: {pending_task.get_name()}, isDone: {pending_task.done()}, state: {pending_task._state}')
            pending_task.cancel()


if __name__ == '__main__':
    # Fix to raise RuntimeError('Event loop is closed')
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(), debug=True)




