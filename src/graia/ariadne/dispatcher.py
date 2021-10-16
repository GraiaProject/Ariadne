from typing import TYPE_CHECKING

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from graia.ariadne.context import application_ctx

if TYPE_CHECKING:
    from graia.ariadne.event.message import MessageEvent

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Source


class MessageChainDispatcher(BaseDispatcher):
    @staticmethod
    async def catch(interface: DispatcherInterface["MessageEvent"]):
        if interface.annotation is MessageChain:
            return interface.event.messageChain


class ApplicationDispatcher(BaseDispatcher):
    @staticmethod
    async def catch(interface: DispatcherInterface):
        if getattr(interface.annotation, "__name__", None) == "GraiaMiraiApplication":
            return application_ctx.get()


class SourceDispatcher(BaseDispatcher):
    @staticmethod
    async def catch(interface: DispatcherInterface["MessageEvent"]):
        if interface.annotation is Source:
            return interface.event.messageChain.getFirst(Source)
