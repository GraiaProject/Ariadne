import asyncio

import pydantic
from devtools import debug
from graia.broadcast import Broadcast
from loguru import logger
from pydantic import BaseModel

from graia.ariadne.console import Console
from graia.ariadne.entry import *
from graia.ariadne.entry.message import *
from graia.ariadne.message.commander import chain_validator


async def main():
    bcc = Broadcast(loop=asyncio.get_running_loop())

    cmd = Commander(bcc)

    def set_perm(group: At, permission: str, value: bool, fast: bool, scope: str):
        logger.info(
            f"Setting {group!r}'s permission {permission} to {value} with scope {scope}, fast: {fast}"
        )

    class Scope(BaseModel):

        _ = pydantic.validator("*", pre=True, allow_reuse=True)(chain_validator)

        scope: str

    cmd.command(
        "[luckperm|lp] group {0} [permission|perm] set {1|permission} {2}",
        {
            "group": Slot(0),
            "permission": Slot(1, type=str),
            "value": Slot(2, type=bool, default=True),
            "scope": Arg(
                "[--scope|-s] {scope}",
                type=Scope,
                default=Scope(scope="global"),
            ),
            "fast": Arg("--fast", default=False),
        },
    )(set_perm)

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
