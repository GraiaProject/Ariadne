from typing import TYPE_CHECKING

from arclet.alconna import Alconna, Arpamar
from arclet.alconna.component import (  # noqa: F401
    CommandInterface,
    Default,
    Option,
    OptionInterface,
    Subcommand,
)
from arclet.alconna.exceptions import (  # noqa: F401
    InvalidFormatMap,
    InvalidOptionName,
    NullName,
    ParamsUnmatched,
)
from arclet.alconna.types import AnyDigit, AnyIP, AnyStr, AnyUrl, Bool  # noqa: F401
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
