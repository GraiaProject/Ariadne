import asyncio

from devtools import debug
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
            "group": Slot(0),
            "permission": Slot(1, type=str),
            "value": Slot(2, type=bool, default=True),
            "scope": Arg("[--scope|-s] {scope}", type=str, default="global"),
            "fast": Arg("--fast", default=True),
        },
    )
    def _(group: At, permission: str, value: bool, fast: bool, scope: str):
        logger.info(
            f"Setting {group!r}'s permission {permission} to {value} with scope {scope}, fast: {fast}"
        )

    try:
        cmd.execute(MessageChain.create("lp group ", At(12345), "error perm set database.read false"))
    except Exception as e:
        debug(e)
    cmd.execute(MessageChain.create("lp group ", At(12345), " perm set database.read false"))
    cmd.execute(MessageChain.create("lp group ", At(12345), " perm set database.read --fast -s global"))
    cmd.execute(MessageChain.create("lp group ", At(12345), " perm set database.read 0 --fast -s local"))
    await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
