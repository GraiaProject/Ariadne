"""Alconna 的简单封装"""
from typing import TYPE_CHECKING

from arclet.alconna import Alconna, Arpamar
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from ...event.message import MessageEvent
from ..chain import MessageChain

if TYPE_CHECKING:
    ArpamarProperty = type("ArpamarProperty", (str, MessageChain), {})
else:
    ArpamarProperty = type("ArpamarProperty", tuple(), {})


class AlconnaDispatcher(BaseDispatcher):
    """
    Alconna的调度器形式
    """

    def __init__(self, *, alconna: Alconna):
        super().__init__()
        self.alconna = alconna

    async def beforeExecution(self, interface: "DispatcherInterface[MessageEvent]"):
        """预处理消息链并存入 local_storage"""
        local_storage = interface.execution_contexts[-1].local_storage
        chain: MessageChain = await interface.lookup_param("message_chain", MessageChain, None, [])
        result = self.alconna.analyse_message(chain)
        local_storage["arpamar"] = result

    async def catch(self, interface: DispatcherInterface[MessageEvent]) -> Arpamar:
        local_storage = interface.execution_contexts[-1].local_storage
        arpamar: Arpamar = local_storage["arpamar"]
        if issubclass(interface.annotation, ArpamarProperty):
            return arpamar.get(interface.name)
        if issubclass(interface.annotation, Arpamar):
            return arpamar
        if issubclass(interface.annotation, Alconna):
            return self.alconna
