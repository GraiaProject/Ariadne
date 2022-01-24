import asyncio
from typing import List

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

        def __str__(self) -> str:
            return self.__repr__()

    def cast_to_list(value: MessageChain, field: ModelField):
        if field.outer_type_ is List[str]:
            return value.asDisplay().split(".")
        if field.outer_type_ is List[MessageChain]:
            return value.split(".")
        return value

    cmd.add_type_cast(cast_to_list)

    @cmd.command(
        "[luckperm | lp] group {0 | target} [permission | perm] set {1 | permission} {value = True}",
        {
            "scope": Arg(
                "[@scope|-s] {scope}",
                type=Scope,
                default=Scope(scope="global"),
            ),
            "fast": Arg("--fast", default=False),
            "perm": Slot(1, List[MessageChain]),
        },
    )
    def set_perm(target: At, perm: List[MessageChain], fast: bool, scope: Scope, value: bool):
        logger.info(f"Setting {target!r}'s permission {perm} to {value} with scope {scope}, fast: {fast}")

    try:
        await cmd.execute(MessageChain.create("lp group ", At(12345), "error perm set database.read false"))
    except Exception as e:
        debug(e)
    await cmd.execute(MessageChain.create("lp group ", At(12345), " perm set database.read false"))
    await cmd.execute(MessageChain.create("lp group ", At(12345), " perm set database.read --fast -s crab"))
    await cmd.execute(
        MessageChain.create("lp group ", At(12345), " perm set database.read 0 --fast -s local")
    )
    await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
