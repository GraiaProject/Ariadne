"""本模块包含许多用于 Ariadne.SendMessage 的 action 函数"""
from typing import NoReturn, Union, overload

from graia.ariadne.model import BotMessage

from ..typing import SendMessageDict, SendMessageException, T


# ANCHOR: bypass
async def bypass(item: T) -> T:
    """
    透传错误的 SendMessage action (有 Exception 时直接返回它而不抛出)

    注意, 请小心 traceback 重生.
    """
    return item


# ANCHOR: strict
@overload
async def strict(item: SendMessageDict) -> SendMessageDict:
    ...


@overload
async def strict(item: SendMessageException) -> NoReturn:
    ...


@overload
async def strict(item: BotMessage) -> BotMessage:
    ...


async def strict(item: Union[SendMessageDict, SendMessageException, BotMessage]):
    """严格的 SendMessage action (有错误时 raise)"""
    if isinstance(item, SendMessageException):
        raise item
    return item


# ANCHOR: ignore
@overload
async def ignore(item: SendMessageDict) -> SendMessageDict:
    ...


@overload
async def ignore(item: SendMessageException) -> None:
    ...


@overload
async def ignore(item: BotMessage) -> BotMessage:
    ...


async def ignore(item: Union[SendMessageDict, SendMessageException, BotMessage]):
    """忽略错误的 SendMessage action (发生 Exception 时 返回 None)"""
    return item if not isinstance(item, Exception) else None


# ANCHOR: safe
@overload
async def safe(item: SendMessageDict) -> SendMessageDict:
    ...


@overload
async def safe(item: SendMessageException) -> None:
    ...


@overload
async def safe(item: BotMessage) -> BotMessage:
    ...


async def safe(item: Union[SendMessageDict, SendMessageException, BotMessage]):
    """
    安全发送的 SendMessage action

    行为: 发送失败时按顺序替换元素为其asDisplay: AtAll, At, Poke, Forward, MultimediaElement
    若最后还是失败 (AccountMuted 等), 则会引发原始异常
    """
    from ..context import ariadne_ctx
    from ..message.chain import MessageChain
    from ..message.element import At, AtAll, Forward, MultimediaElement, Plain, Poke

    if not isinstance(item, Exception):
        return item

    chain: MessageChain = item.send_data["message"]
    ariadne = ariadne_ctx.get()

    def convert(msg_chain: MessageChain, type) -> None:
        for ind, elem in enumerate(msg_chain.__root__[:]):
            if isinstance(elem, type):
                msg_chain.__root__[ind] = Plain(elem.asDisplay())

    item.send_data["quote"] = False
    val = await ariadne.sendMessage(**item.send_data, action=ignore)
    if val is not None:
        return val

    for type in [AtAll, At, Poke, Forward, MultimediaElement]:
        convert(chain, type)
        val = await ariadne.sendMessage(**item.send_data, action=ignore)
        if val is not None:
            return val

    raise item
