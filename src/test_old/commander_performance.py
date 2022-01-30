import asyncio
import time

from devtools import debug

from graia.ariadne.entry.message import *
from graia.ariadne.message.commander import Arg, Commander, Slot
from graia.ariadne.util import Dummy

RUN = 20000

if __name__ == "__main__":

    async def m():
        cmd = Commander(Dummy())

        msg = MessageChain.create(".test", " --foo ", At(123))

        @cmd.command(".test --foo {v}")
        def _(v: At = None):
            print(v)

        @cmd.command(".test --foo {v}")
        def _(v: At = None):
            print(v)

        @cmd.command(".test --foo {v}")
        def _(v: At = None):
            print(v)

        async def disp(x):
            debug(x.dispatchers[0].data)

        cmd.broadcast.Executor = disp

        await cmd.execute(msg)
        cmd.broadcast.Executor = Dummy()

        li: list[int] = []

        for _ in range(RUN):
            st = time.thread_time_ns()
            await cmd.execute(msg)
            ed = time.thread_time_ns()
            li.append(ed - st)

        print(
            f"Commander: {sum(li) / RUN} ns per loop with {RUN} loops, {len(cmd.command_handlers)} handlers"
        )

    asyncio.run(m())
