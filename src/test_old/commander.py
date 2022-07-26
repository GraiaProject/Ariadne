import asyncio
from typing import List, Sequence, Tuple

import pydantic
import rich.traceback
from devtools import debug
from graia.broadcast import Broadcast
from loguru import logger
from pydantic import BaseModel
from pydantic.fields import ModelField

from graia.ariadne.console import Console
from graia.ariadne.entry import At, MessageChain
from graia.ariadne.message.commander import Arg, Commander, Slot, chain_validator

rich.traceback.install(show_locals=True)


async def main():
    bcc = Broadcast(loop=asyncio.get_running_loop())

    cmd = Commander(bcc)

    class Scope(BaseModel):

        _ = pydantic.validator("*", pre=True, allow_reuse=True)(chain_validator)

        scope: str

        def __str__(self) -> str:
            return self.__repr__()

    def cast_to_list(value: MessageChain, field: ModelField):
        if not isinstance(value, MessageChain):
            return value
        if field.outer_type_ is List[str]:
            return value.display.split(".")
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
    def set_perm_simple(target: At, perm: List[MessageChain], fast: bool, scope: Scope, value: bool):
        logger.info(
            f"Simplified: Setting {target!r}'s permission {perm} to {value} with scope {scope}, fast: {fast}"
        )

    @cmd.command(
        r"[luckperm | lp] group {0 | target} [permission | perm] set {perm: List\[MessageChain\]} {value = True}",
        {
            "scope": Arg(
                "[@scope|-s] {scope}",
                type=Scope,
                default=Scope(scope="global"),
            ),
        },
    )
    def set_perm(
        target: At,
        perm: List[MessageChain],
        scope: Scope,
    ):
        logger.info(f"Setting {target!r}'s permission {perm} with scope {scope}")

    @cmd.command("[download_image|img] {...images}", {"images": Slot("images", "raw")})
    def get_img(images):
        logger.info(repr(images))

    @cmd.command("[download_image|img] {...images:str}")
    def get_img(images):
        logger.info(repr(images))

    @cmd.command("record {title: str = ''} {...targets: At}", {"help": Arg("--help")})
    def log_targets(title: str, targets: Sequence[At], help: bool):
        logger.info(title)
        logger.info(targets)
        logger.info(help)

    @cmd.command("&test {param}", {"param": Slot("param", str, "")})
    def al(param: str):
        print("Param", param)

    await cmd.execute(MessageChain("lp group ", At(12345), "error perm set database.read false"))
    debug("Nothing")
    await cmd.execute(MessageChain("lp group ", At(12345), " perm set database.read false"))
    debug("db read 1")
    await cmd.execute(MessageChain("lp group ", At(23456), " perm set system.overload --fast -s crab"))
    debug("sys overload 1")
    await cmd.execute(MessageChain("lp group ", At(12345), " perm set database.read 0 --fast -s local"))
    debug("db read 2")
    await cmd.execute(MessageChain("img img.net/1 img.net/2 img.net/3"))
    debug("wildcard")
    await cmd.execute(MessageChain("record --help"))
    await cmd.execute(MessageChain("record example-talk ", At(1), " ", At(2), " ", At(3), " --help"))
    await cmd.execute(MessageChain("&test type"))
    debug("targets")


if __name__ == "__main__":
    asyncio.run(main())
