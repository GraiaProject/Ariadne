"""Ariadne 内置的 Dispatcher"""
from typing import TYPE_CHECKING

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from .context import adapter_ctx, ariadne_ctx, broadcast_ctx, event_loop_ctx
from .message.chain import MessageChain
from .message.element import Source

if TYPE_CHECKING:
    from .app import Ariadne
    from .event.message import MessageEvent


class MessageChainDispatcher(BaseDispatcher):
    """从 MessageEvent 提取 MessageChain 的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface["MessageEvent"]):
        if interface.annotation is MessageChain:
            return interface.event.messageChain


class MiddlewareDispatcher(BaseDispatcher):
    """分发 Ariadne 等基础参数的 Dispatcher"""

    def __init__(self, app: "Ariadne") -> None:
        self.app: "Ariadne" = app

    async def catch(self, interface: DispatcherInterface):
        from asyncio import AbstractEventLoop

        from graia.broadcast import Broadcast

        from .adapter import Adapter
        from .app import Ariadne

        if issubclass(interface.annotation, Ariadne):
            return self.app
        if issubclass(interface.annotation, Broadcast):
            return self.app.broadcast
        if issubclass(interface.annotation, AbstractEventLoop):
            return self.app.loop
        if issubclass(interface.annotation, Adapter):
            return self.app.adapter


class ContextDispatcher(BaseDispatcher):
    """提取上下文的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        from asyncio import AbstractEventLoop

        from graia.broadcast import Broadcast

        from .adapter import Adapter
        from .app import Ariadne

        if not isinstance(interface.annotation, type):
            return
        if issubclass(interface.annotation, Ariadne):
            return ariadne_ctx.get()
        if issubclass(interface.annotation, Broadcast):
            return broadcast_ctx.get()
        if issubclass(interface.annotation, AbstractEventLoop):
            return event_loop_ctx.get()
        if issubclass(interface.annotation, Adapter):
            return adapter_ctx.get()
        if issubclass(interface.annotation, Dispatchable):
            return interface.event


class SourceDispatcher(BaseDispatcher):
    """提取 MessageEvent 消息链 Source 元素的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface["MessageEvent"]):
        if interface.annotation is Source:
            return interface.event.messageChain.getFirst(Source)
