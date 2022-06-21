import asyncio
import time

from devtools import debug
from graia.broadcast import Broadcast

from graia.ariadne.entry.message import *
from graia.ariadne.message.commander import Arg, Commander, Slot
from graia.ariadne.util import Dummy

RUN = 1000

if __name__ == "__main__":

    async def m():
        cmd = Commander(Broadcast(loop=asyncio.get_running_loop()))

        msg = MessageChain(".test", " --foo ", At(123))

        @cmd.command(".test --foo {v}")
        def _(v: At = None):
            ...

        @cmd.command(".test --foo {v}")
        def _(v: At = None):
            ...

        @cmd.command(".test --foo {v}")
        def _(v: At = None):
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

        print(f"Commander: {RUN/sec} loop/s, {RUN} loops, 15 handlers")

    asyncio.run(m())
