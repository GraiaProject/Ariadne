import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))


import asyncio

from graia.ariadne.util.async_exec import ParallelExecutor, cpu_bound


@cpu_bound
def fact(x: int):
    res: int = 1
    while x != 1:
        res *= x
        x -= 1
    return res


if __name__ == "__main__":

    async def main():
        loop = asyncio.get_running_loop()
        ParallelExecutor().bind_loop(loop)
        import time

        st = time.time()
        tsk1 = asyncio.create_task(fact(50000))
        tsk2 = asyncio.create_task(fact(50000))
        await tsk1
        await tsk2
        print(time.time() - st)
        st = time.time()
        fact.__wrapped__(50000)
        fact.__wrapped__(50000)
        print(time.time() - st)

    asyncio.run(main())
