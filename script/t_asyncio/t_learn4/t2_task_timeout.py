"""
1、取消任务
2、设置超时并使用wait_for执行取消
3、保护任务免于取消
"""
import asyncio
from asyncio import CancelledError


async def delay(i) -> None:
    await asyncio.sleep(i)
    print(f'delay {i}s is OK.')


async def main_cancel_task() -> None:
    """ 取消任务 """
    task = asyncio.create_task(delay(10))
    elapsed = 0

    # 取消任务
    while not task.done():
        print(f'Task not finished, checking again in a second.')
        await asyncio.sleep(1)

        elapsed += 1
        if elapsed >= 5:
            task.cancel()

    try:
        await task
    except CancelledError:
        print('Our task was cancelled!')


async def main_wait_for() -> None:
    """ 设置超时并使用wait_for执行取消 """
    task = asyncio.create_task(delay(2))

    try:
        ret = await asyncio.wait_for(task, timeout=1)
        print(ret)
    except asyncio.TimeoutError:
        print("got a timeout!!!")
        print(f"Was the task cancelled? {task.cancelled()}")
    else:
        print(f'Task was done, state: {task.done()}')


async def main_shield_task() -> None:
    """ 保护任务免于取消 """
    task = asyncio.create_task(delay(3))

    try:
        # asyncio.shield: 即使给任务设置了1s超时，但是shield会屏蔽这个超时
        ret = await asyncio.wait_for(asyncio.shield(task), timeout=1)
        print(ret)
    except asyncio.TimeoutError:
        print("got a timeout!!!")
        print(f"Was the task cancelled? {task.cancelled()}")
        ret = await task
        print(f'X ret: {ret}')
    else:
        print(f'Task was done, state: {task.done()}')


# asyncio.run(main_cancel_task())
# asyncio.run(main_wait_for())
asyncio.run(main_shield_task())


