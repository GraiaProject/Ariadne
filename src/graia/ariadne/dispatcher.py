"""Ariadne 内置的 Dispatcher"""
from typing import TYPE_CHECKING

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from .context import ariadne_ctx
from .message.chain import MessageChain
from .message.element import Source

if TYPE_CHECKING:
    from .event.message import MessageEvent


class MessageChainDispatcher(BaseDispatcher):
    """从 MessageEvent 提取 MessageChain 的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface["MessageEvent"]):
        if interface.annotation is MessageChain:
            return interface.event.messageChain


class ApplicationDispatcher(BaseDispatcher):
    """提取 Ariadne 实例的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        if getattr(interface.annotation, "__name__", None) == "Ariadne":
            return ariadne_ctx.get()


class SourceDispatcher(BaseDispatcher):
    """提取 MessageEvent 消息链 Source 元素的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface["MessageEvent"]):
        if interface.annotation is Source:
            return interface.event.messageChain.getFirst(Source)
