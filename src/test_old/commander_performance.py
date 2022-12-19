import asyncio
import time

from devtools import debug

from graia.ariadne.entry.message import *
from graia.ariadne.message.commander import Commander
from graia.broadcast import Broadcast

RUN = 10000

if __name__ == "__main__":

    async def m():
        cmd = Commander(Broadcast(loop=asyncio.get_running_loop()))

        msg = MessageChain(".test foo bar fox mop ", At(123))

        handles = 15

        for _ in range(handles):

            @cmd.command(".test foo bar fox mop {v}")
            def _(v: At):
                ...

        async def disp(entry, dispatchers):
            debug(dispatchers[0].data)

        exec = cmd.broadcast.Executor

        cmd.broadcast.Executor = disp

        await cmd.execute(msg)

        async def a(*args, **kwargs):
            ...

        cmd.broadcast.Executor = a

        sec: float = 0.0

        for _ in range(RUN):
            st = time.time()
            await cmd.execute(msg)
            ed = time.time()
            sec += ed - st


    asyncio.run(m())
