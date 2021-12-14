from typing import TYPE_CHECKING

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from ....event.message import MessageEvent
from ...chain import MessageChain
from .alconna import (
    Alconna,
    AnyDigit,
    AnyIP,
    AnyStr,
    AnyUrl,
    Arpamar,
    CommandInterface,
    Option,
    OptionInterface,
    Subcommand,
)
from .alconna.exceptions import InvalidOptionName, NullName, ParamsUnmatched

if TYPE_CHECKING:

    class ArpamarProperty(str, MessageChain):
        """用于指示 Arpamar 属性的 type hint."""

        pass

else:

    class ArpamarProperty:
        pass


class AlconnaDispatcher(BaseDispatcher):
    """
    Alconna的调度器形式
    """

    def __init__(self, *, alconna: Alconna):
        super().__init__()
        self.alconna = alconna

    def beforeExecution(self, interface: "DispatcherInterface[MessageEvent]"):
        local_storage = interface.execution_contexts[-1].local_storage
        chain: MessageChain = interface.event.messageChain
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