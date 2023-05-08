"""本模块包含许多用于 Ariadne.SendMessage 的 action 函数"""
from typing import Optional, TypeVar, Union, overload

from ..app import Ariadne
from ..event.message import ActiveMessage
from ..exception import RemoteException, UnknownError, UnknownTarget
from ..typing import SendMessageAction, SendMessageException

Exc_T = TypeVar("Exc_T", bound=SendMessageException)


# ANCHOR: bypass
class Bypass(SendMessageAction):
    """
    透传错误的 SendMessage action (有 Exception 时直接返回它而不抛出)

    注意, 请小心 traceback 重生.
    """

    @staticmethod
    async def exception(item: Exc_T) -> Exc_T:
        return item


# ANCHOR: strict
class Strict(SendMessageAction):
    """严格的 SendMessage action (有错误时 raise)"""

    ...


# ANCHOR: ignore
class Ignore(SendMessageAction):
    """忽略错误的 SendMessage action (发生 Exception 时 返回 None)"""

    @staticmethod
    async def exception(_) -> None:
        return


# ANCHOR: safe


class Safe(SendMessageAction):
    """
    安全发送的 SendMessage action

    行为:
    在第一次尝试失败后先移除 quote,
    之后每次失败时按顺序替换元素为其 str 形式: AtAll, At, Poke, Forward, MultimediaElement

    仅会对以下错误进行重试:

    - `UnknownTarget` (指向对象不存在，可能由移除成员等行为引发竞争)
    - `RemoteException` (网络问题)
    - `UnknownError` (其他由 RPC 引发的未知错误)
    """

    def __init__(self, ignore: bool = False) -> None:
        self.ignore: bool = ignore

    @overload
    @staticmethod
    async def exception(item) -> ActiveMessage:
        ...

    @overload
    async def exception(self, item) -> ActiveMessage:
        ...

    @staticmethod
    async def _handle(item: SendMessageException, ignore: bool):
        from ..message.chain import MessageChain
        from ..message.element import At, AtAll, Forward, MultimediaElement, Plain, Poke

        chain: MessageChain = item.send_data["message"]
        ariadne = Ariadne.current()

        def convert(msg_chain: MessageChain, type) -> None:
            for ind, elem in enumerate(msg_chain.__root__[:]):
                if isinstance(elem, type):
                    msg_chain.__root__[ind] = Plain(elem.display)

        for type in [AtAll, At, Poke, Forward, MultimediaElement]:
            convert(chain, type)
            try:
                val = await ariadne.send_message(**item.send_data, action=Strict)  # type: ignore
            except (UnknownTarget, RemoteException, UnknownError):  # 这些错误可以继续重试
                continue
            except SendMessageException:  # 其他错误
                break
            return val

        if not ignore:
            raise item

    @overload
    @staticmethod
    async def exception(s, i):
        ...

    @overload
    async def exception(s, i):  # sourcery skip: instance-method-first-arg-name
        ...

    async def exception(s: Union["Safe", Exc_T], i: Optional[Exc_T] = None):  # type: ignore
        # sourcery skip: instance-method-first-arg-name
        if not isinstance(s, Safe):
            return await Safe._handle(s, True)
        if i:
            return await Safe._handle(i, s.ignore)
