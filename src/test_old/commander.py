import asyncio

import pydantic
from devtools import debug
from graia.broadcast import Broadcast
from loguru import logger
from pydantic import BaseModel
from pydantic.fields import ModelField

from graia.ariadne.console import Console
from graia.ariadne.entry import *
from graia.ariadne.entry.message import *
from graia.ariadne.message.commander import chain_validator


async def main():
    bcc = Broadcast(loop=asyncio.get_running_loop())

    cmd = Commander(bcc)

    class Scope(BaseModel):

        _ = pydantic.validator("*", pre=True, allow_reuse=True)(chain_validator)

        scope: str

    def cast_to_list(value: MessageChain, field: ModelField):
        if field.type_ is list:
            return list(value)
        return value

    cmd.add_type_caster(cast_to_list)

    @cmd.command(
        "[luckperm|lp] group {0|target} [permission|perm] set {1|permission} {2|value}",
        {
            "scope": Arg(
                "[--scope|-s] {scope}",
                type=Scope,
                default=Scope(scope="global"),
            ),
            "fast": Arg("--fast", default=False),
        },
    )
    def set_perm(target: list, permission: str, fast: bool, scope: Scope, value: bool = True):
        logger.info(
            f"Setting {target!r}'s permission {permission} to {value} with scope {scope}, fast: {fast}"
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
