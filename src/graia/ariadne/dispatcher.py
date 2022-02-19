"""Ariadne 内置的 Dispatcher"""

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from .message.chain import MessageChain
from .message.element import Source


class MessageChainDispatcher(BaseDispatcher):
    """从 MessageEvent 提取 MessageChain 的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        from .event.message import MessageEvent

        if isinstance(interface.event, MessageEvent):
            if interface.annotation is MessageChain:
                return interface.event.messageChain


class ContextDispatcher(BaseDispatcher):
    """提取上下文的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        from . import get_running

        if not isinstance(interface.annotation, type):
            return
        if issubclass(interface.annotation, Dispatchable):
            return interface.event

        return get_running(interface.annotation)


class SourceDispatcher(BaseDispatcher):
    """提取 MessageEvent 消息链 Source 元素的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        from .event.message import MessageEvent

        if isinstance(interface.event, MessageEvent):
            if interface.annotation is Source:
                return interface.event.messageChain.getFirst(Source)


class SenderDispatcher(BaseDispatcher):
    """
    从 MessageEvent 提取 sender 的 Dispatcher.
    支持实现了 __instancecheck__ 的注释, 如 Union, Optional (Python 3.10+)
    和被 typing.runtime_checkable 标记为运行时协议的 Protocol.
    """

    @staticmethod
    async def catch(interface: DispatcherInterface):
        from .event.message import MessageEvent

        if isinstance(interface.event, MessageEvent):
            try:
                if isinstance(interface.event.sender, interface.annotation):
                    return interface.event.sender
            except TypeError:
                pass
