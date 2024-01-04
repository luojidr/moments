"""
处理cpu密集型的任务，即使使用协程，也不回让程序提高性能，asyncio旨在提高io的并发，而不是cpu
"""
import asyncio

from script.t_asyncio.t_learn4.t4_async_timed import async_timed, delay


@async_timed()
async def cpu_bound_work():
    counter = 0
    for i in range(50000000):
        counter += 1

    return counter


@async_timed()
async def main_trap():
    task1 = asyncio.create_task(cpu_bound_work())
    task2 = asyncio.create_task(cpu_bound_work())

    await task1
    await task2


@async_timed()
async def main_trap2():
    # delay_task = asyncio.create_task(delay(6))  # 先创建io协程，先被注册事件循环的任务队列中，不论何时 await 会被优先挂起执行
    task1 = asyncio.create_task(cpu_bound_work())
    task2 = asyncio.create_task(cpu_bound_work())
    delay_task = asyncio.create_task(delay(6))  # 后创建io协程，最后被注册事件循环的任务队列中，等待其他的任务被执行完或被挂起才回被执行

    await task1
    await task2
    await delay_task


if __name__ == '__main__':
    # asyncio.run(main_trap())  # Cost time 12.3402 second(s), 平均每个6秒，与同步阻塞一样

    # Cost time 18.2815 second(s)
    # cpu_bound_work 同步执行，最后才是delay_task协程，因为没有其他关于io的协程可以执行了，只能慢慢的耗时6s后执行结束
    asyncio.run(main_trap2())
