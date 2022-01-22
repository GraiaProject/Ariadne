"""Ariadne 内置的 Dispatcher"""
from typing import TYPE_CHECKING, ContextManager, TypedDict

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from .context import (
    adapter_ctx,
    ariadne_ctx,
    broadcast_ctx,
    enter_context,
    event_loop_ctx,
)
from .message.chain import MessageChain
from .message.element import Source

if TYPE_CHECKING:
    from .app import Ariadne


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


class ContextLC(TypedDict):
    """local storage 表示"""

    __CONTEXT_MANAGER__: ContextManager


class MiddlewareDispatcher(BaseDispatcher):
    """分发 Ariadne 等基础参数的 Dispatcher"""

    def __init__(self, app: "Ariadne") -> None:
        self.app: "Ariadne" = app

    async def catch(self, interface: DispatcherInterface):
        return await ContextDispatcher.catch(interface)

    async def beforeExecution(self, interface: DispatcherInterface):
        """进入事件分发上下文"""
        lc: ContextLC = interface.execution_contexts[-1].local_storage  # type: ignore
        lc["__CONTEXT_MANAGER__"] = enter_context(self.app, interface.event)
        lc["__CONTEXT_MANAGER__"].__enter__()

    async def afterExecution(self, interface: DispatcherInterface, *_):
        """退出事件分发上下文"""
        lc: ContextLC = interface.execution_contexts[-1].local_storage  # type: ignore
        lc["__CONTEXT_MANAGER__"].__exit__(None, None, None)


class SourceDispatcher(BaseDispatcher):
    """提取 MessageEvent 消息链 Source 元素的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        from .event.message import MessageEvent

        if isinstance(interface.event, MessageEvent):
            if interface.annotation is Source:
                return interface.event.messageChain.getFirst(Source)
