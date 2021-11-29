from typing import TYPE_CHECKING

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from .context import ariadne_ctx

if TYPE_CHECKING:
    from .event.message import MessageEvent

from .message.chain import MessageChain
from .message.element import Source


class MessageChainDispatcher(BaseDispatcher):
    @staticmethod
    async def catch(interface: DispatcherInterface["MessageEvent"]):
        if interface.annotation is MessageChain:
            return interface.event.messageChain


class ApplicationDispatcher(BaseDispatcher):
    @staticmethod
    async def catch(interface: DispatcherInterface):
        if getattr(interface.annotation, "__name__", None) == "Ariadne":
            return ariadne_ctx.get()


class SourceDispatcher(BaseDispatcher):
    @staticmethod
    async def catch(interface: DispatcherInterface["MessageEvent"]):
        if interface.annotation is Source:
            return interface.event.messageChain.getFirst(Source)
