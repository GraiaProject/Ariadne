import asyncio

from graia.broadcast import Broadcast
from loguru import logger

from graia.ariadne.entry import *
from graia.ariadne.entry.message import *


async def main():
    bcc = Broadcast(loop=asyncio.get_running_loop())

    cmd = Commander(bcc)

    @cmd.command(
        "[luckperm|lp] group {0} [permission|perm] set {1|permission} {2}",
        {
            "group": Slot(0, type=At),
            "permission": Slot(1, type=str),
            "value": Slot(2, type=bool, default=True),
            "scope": Arg("[--scope|-s] {scope|0}", lambda x: x["scope"].asDisplay()),
            "fast": Arg("--fast"),
        },
    )
    def _(group: ..., permission: str, value: bool, fast: bool, scope: str):
        logger.info(f"Setting {group}'s permission {permission} to {value} with scope {scope}, fast: {fast}")

    cmd.execute(MessageChain.create("lp group ", At(12345), "error perm set database.read false"))
    cmd.execute(MessageChain.create("lp group ", At(12345), " perm set database.read false"))
    cmd.execute(MessageChain.create("lp group ", At(12345), " perm set database.read 0 --fast -s global"))
    await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
