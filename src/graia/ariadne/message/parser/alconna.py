"""Alconna 的简单封装

Important: 建议手动从 `arclet.alconna` 导入其他部分"""
import traceback
from typing import TYPE_CHECKING

from arclet.alconna import (
    Alconna,
    Arpamar,
    MessageChain,
    NonTextElement,
    ParamsUnmatched,
    change_help_send_action,
)
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.signatures import Force
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from ... import get_running
from ...app import Ariadne
from ...event.message import MessageEvent
from ..chain import MessageChain as GraiaMessageChain

if TYPE_CHECKING:
    ArpamarProperty = type("ArpamarProperty", (str, MessageChain, NonTextElement), {})
else:
    ArpamarProperty = type("ArpamarProperty", (), {})


class AlconnaDispatcher(BaseDispatcher):
    """
    Alconna的调度器形式
    """

    def __init__(self, *, alconna: Alconna, reply_help: bool = False, skip_for_unmatch: bool = True):
        """
        构造 Alconna调度器

        Args:
            alconna (Alconna): Alconna实例
            reply_help (bool): 是否自助回复帮助信息给指令的发起者, 默认为 False
            skip_for_unmatch (bool): 当指令匹配失败时是否跳过对应的事件监听器, 默认为 True
        """
        super().__init__()
        self.alconna = alconna
        self.reply_help = reply_help
        self.skip_for_unmatch = skip_for_unmatch
        if not reply_help:
            change_help_send_action(lambda x: x)

    async def beforeExecution(self, interface: "DispatcherInterface[MessageEvent]"):
        """预处理消息链并存入 local_storage"""
        if self.reply_help:
            event: MessageEvent = await interface.lookup_param("event", MessageEvent, None)
            app: Ariadne = get_running()

            def _send_help_string(help_string: str):
                app.loop.create_task(app.sendMessage(event.sender, GraiaMessageChain.create(help_string)))

            change_help_send_action(_send_help_string)

        local_storage = interface.local_storage
        chain: GraiaMessageChain = await interface.lookup_param("message_chain", GraiaMessageChain, None)
        result = self.alconna.analyse_message(chain)
        try:
            result = self.alconna.analyse_message(chain)
        except ParamsUnmatched:
            traceback.print_exc()
            raise ExecutionStop
        if not result.matched and self.skip_for_unmatch:
            raise ExecutionStop
        local_storage["arpamar"] = result

    async def catch(self, interface: DispatcherInterface[MessageEvent]):
        local_storage = interface.local_storage
        arpamar: Arpamar = local_storage["arpamar"]
        if issubclass(interface.annotation, Arpamar):
            return arpamar
        if issubclass(interface.annotation, Alconna):
            return self.alconna
        if isinstance(interface.annotation, dict) and arpamar.options.get(interface.name):
            return arpamar.options[interface.name]
        if interface.name in arpamar.all_matched_args:
            if isinstance(arpamar.all_matched_args[interface.name], interface.annotation):
                return arpamar.all_matched_args[interface.name]
        if issubclass(interface.annotation, ArpamarProperty):
            return arpamar.get(interface.name)
        return Force()
