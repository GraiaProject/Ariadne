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
    compile,
)
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities.signatures import Force
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from ... import get_running
from ...app import Ariadne
from ...dispatcher import ContextDispatcher
from ...event.message import MessageEvent
from ..chain import MessageChain as GraiaMessageChain

if TYPE_CHECKING:
    ArpamarProperty = type("ArpamarProperty", (str, MessageChain, NonTextElement), {})
else:
    ArpamarProperty = type("ArpamarProperty", (), {})


class AlconnaHelpMessage(Dispatchable):
    """
    Alconna帮助信息发送事件

    如果触发的某个命令的帮助选项, 当AlconnaDisptcher的reply_help为False时, 会发送该事件
    """

    command: Alconna
    """命令"""

    help_string: str
    """帮助信息"""

    def __init__(self, alconna: Alconna, help_string: str):
        self.command = alconna
        self.help_string = help_string

    class Dispatcher(BaseDispatcher):
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: "DispatcherInterface[AlconnaHelpMessage]"):
            if interface.name == "help_string" and interface.annotation == str:
                return interface.event.help_string
            if interface.annotation == Alconna:
                return interface.event.command


class AlconnaDispatcher(BaseDispatcher):
    """
    Alconna的调度器形式
    """

    def __init__(self, *, alconna: Alconna, reply_help: bool = False, skip_for_unmatch: bool = True):
        """
        构造 Alconna调度器

        Args:
            alconna (Alconna): Alconna实例
            reply_help (bool): 是否自助回复帮助信息给指令的发起者. 当为 False 时, 会广播一个'AlconnaHelpMessage'事件以交给用户处理帮助信息.
            skip_for_unmatch (bool): 当指令匹配失败时是否跳过对应的事件监听器, 默认为 True
        """
        super().__init__()
        self.analyser = compile(alconna)
        self.reply_help = reply_help
        self.skip_for_unmatch = skip_for_unmatch

    async def beforeExecution(self, interface: "DispatcherInterface[MessageEvent]"):
        """预处理消息链并存入 local_storage"""
        event: MessageEvent = await interface.lookup_param("event", MessageEvent, None)

        if self.reply_help:
            app: Ariadne = get_running()

            async def _send_help_string(help_string: str):
                await app.sendMessage(event.sender, GraiaMessageChain.create(help_string))

            change_help_send_action(_send_help_string)
        else:

            def _post_help(help_string: str):
                interface.broadcast.postEvent(
                    AlconnaHelpMessage(self.analyser.alconna, help_string), upper_event=event
                )

            change_help_send_action(_post_help)

        local_storage = interface.local_storage
        chain: GraiaMessageChain = await interface.lookup_param("message_chain", GraiaMessageChain, None)
        try:
            result = self.analyser.analyse(chain)
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
            return self.analyser.alconna
        if isinstance(interface.annotation, dict) and arpamar.options.get(interface.name):
            return arpamar.options[interface.name]
        if interface.name in arpamar.all_matched_args:
            if isinstance(arpamar.all_matched_args[interface.name], interface.annotation):
                return arpamar.all_matched_args[interface.name]
        if issubclass(interface.annotation, ArpamarProperty):
            return arpamar.get(interface.name)
        return Force()
