"""本模块包含许多用于 Ariadne.SendMessage 的 action 函数"""
from typing import Optional, TypeVar, Union, overload

from .. import get_running
from ..model import BotMessage
from ..typing import SendMessageAction, SendMessageException

Exc_T = TypeVar("Exc_T", bound=SendMessageException)


# ANCHOR: bypass
class Bypass(SendMessageAction):
    """
    透传错误的 SendMessage action (有 Exception 时直接返回它而不抛出)

    注意, 请小心 traceback 重生.
    """

    @staticmethod
    async def exception(item: Exc_T, /) -> Exc_T:
        return item


# ANCHOR: strict
class Strict(SendMessageAction):
    """严格的 SendMessage action (有错误时 raise)"""

    ...


# ANCHOR: ignore
class Ignore(SendMessageAction):
    """忽略错误的 SendMessage action (发生 Exception 时 返回 None)"""

    @staticmethod
    async def exception(_: Exc_T, /) -> Exc_T:
        return None


# ANCHOR: safe


class Safe(SendMessageAction):
    """
    安全发送的 SendMessage action

    行为:
    在第一次尝试失败后先移除 quote,
    之后每次失败时按顺序替换元素为其asDisplay: AtAll, At, Poke, Forward, MultimediaElement
    若最后还是失败 (AccountMuted 等), 则会引发原始异常 (通过传入 ignore 决定)
    """

    def __init__(self, ignore: bool = False) -> None:
        self.ignore: bool = ignore

    @overload
    @staticmethod
    async def exception(item: Exc_T, /) -> BotMessage:
        ...

    @overload
    async def exception(self, item: Exc_T, /) -> BotMessage:
        ...

    @staticmethod
    async def _handle(item: Exc_T, ignore: bool):
        from ..message.chain import MessageChain
        from ..message.element import At, AtAll, Forward, MultimediaElement, Plain, Poke

        chain: MessageChain = item.send_data["message"]
        ariadne = get_running()

        def convert(msg_chain: MessageChain, type) -> None:
            for ind, elem in enumerate(msg_chain.__root__[:]):
                if isinstance(elem, type):
                    msg_chain.__root__[ind] = Plain(elem.asDisplay())

        for type in [AtAll, At, Poke, Forward, MultimediaElement]:
            convert(chain, type)
            val = await ariadne.sendMessage(**item.send_data, action=Ignore)
            if val is not None:
                return val

        if not ignore:
            raise item

    async def exception(s: Union["Safe", Exc_T], i: Optional[Exc_T] = None):
        if isinstance(s, Safe):
            return await Safe._handle(i, s.ignore)
        return await Safe._handle(s, True)
