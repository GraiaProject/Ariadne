"""Ariadne 控制台
注意, 本实现并不 robust, 但是可以使用"""

import contextlib
import importlib.metadata
import sys
from asyncio.events import AbstractEventLoop
from asyncio.tasks import Task
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from graia.broadcast import Broadcast
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.exectarget import ExecTarget
from graia.broadcast.exceptions import DisabledNamespace, PropagationCancelled
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from loguru import logger
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.patch_stdout import StdoutProxy
from prompt_toolkit.shortcuts.prompt import PromptSession
from prompt_toolkit.styles import Style

from ..dispatcher import ContextDispatcher
from ..event.lifecycle import ApplicationLaunched, ApplicationShutdowned
from ..util import resolve_dispatchers_mixin


class Console:
    """Ariadne 的控制台, 可以脱离 Ariadne 实例运行
    警告: 本实现无法确保稳定性"""

    def __init__(
        self,
        broadcast: Broadcast,
        prompt: Union[Callable[[], str], AnyFormattedText] = "{library_name} {graia_ariadne_version}>",
        *,
        r_prompt: Union[Callable[[], str], AnyFormattedText] = "",
        style: Optional[Style] = None,
        extra_data_getter: Iterable[Callable[[], Dict[str, Any]]] = (),
        replace_logger: bool = True,
        listen_launch: bool = True,
        listen_shutdown: bool = True,
    ) -> None:
        """初始化控制台.

        Args:
            broadcast (Broadcast): 事件系统.
            prompt (AnyFormattedText, optional): 输入提示, 可使用 f-string 形式的格式化字符串. \
            默认为 "{library_name} {graia_ariadne_version}>".
            r_prompt (AnyFormattedText, optional): 右侧提示, 可使用 f-string 形式的格式化字符串. 默认为空.
            style (Style, optional): 输入提示的格式, 详见 prompt_toolkit 的介绍.
            extra_data_getter (Iterable[() -> Dict[str, Any], optional): 额外的 Callable, 用于生成 prompt 的格式化数据.
            replace_logger (bool, optional): 是否尝试替换 loguru 的 0 号 handler (sys.stderr) 为 StdoutProxy. 默认为 True.
            listen_launch (bool, optional): 是否监听 Ariadne 的 ApplicationLaunched 事件并启动自身, 默认为 True.
            listen_shutdown (bool, optional): 是否监听 Ariadne 的 ApplicationShutdowned 事件并停止自身, 默认为 True.
        """
        self.broadcast = broadcast

        # Handle Ariadne Event
        if listen_launch:
            broadcast.receiver(ApplicationLaunched)(self.start)

        if listen_shutdown:
            broadcast.receiver(ApplicationShutdowned)(self.stop)

        self.session: PromptSession[str] = PromptSession()

        self.style = style or Style([])

        self.l_prompt: AnyFormattedText = prompt
        self.r_prompt: AnyFormattedText = r_prompt

        self.registry: List[Tuple[Callable, List[BaseDispatcher], List[Decorator]]] = []
        self.extra_data_getter = extra_data_getter

        self.running: bool = False
        self.task: Optional[Task] = None

        self.handler_id: int = 0
        self.replace_logger: bool = replace_logger

        logger.warning("Please note that console is NOT STABLE.")
        logger.warning("Use it at your own risk.")

    def data_getter(self) -> Dict[str, Any]:
        """返回用于 prompt 的数据

        Returns:
            Dict[str, Any]: 可用于 format_map 的数据字典
        """
        data = {
            "library_name": "Ariadne",
        }

        for dist in importlib.metadata.distributions():
            name: str = dist.metadata["Name"]
            version: str = dist.version
            if name.startswith("graia"):
                if name == "graia-ariadne-dev":
                    name = "graia-ariadne"
                data[f"{'_'.join(name.split('-') + ['version'])}"] = version

        for func in self.extra_data_getter:
            data.update(func())

        return data

    async def prompt(
        self,
        l_prompt: Optional[AnyFormattedText] = None,
        r_prompt: Optional[AnyFormattedText] = None,
        style: Optional[Style] = None,
    ) -> str:
        """向控制台发送一个输入请求, 异步

        Args:
            l_prompt (AnyFormattedText, optional): 左输入提示, 可使用 f-string 形式的格式化字符串. \
            默认为 "{library_name} {graia_ariadne_version}>". 注意为 l_prompt .
            r_prompt (AnyFormattedText, optional): 右侧提示, 可使用 f-string 形式的格式化字符串. 默认为空.
            style (Style, optional): 输入提示的格式, 详见 prompt_toolkit 的介绍.

        Returns:
            str: 输入结果
        """
        l_prompt = l_prompt or self.l_prompt
        r_prompt = r_prompt or self.r_prompt
        style = style or self.style
        if isinstance(l_prompt, str):
            l_prompt = l_prompt.format_map(self.data_getter())

        if isinstance(r_prompt, str):
            r_prompt = r_prompt.format_map(self.data_getter())

        try:
            return await self.session.prompt_async(
                message=l_prompt,
                rprompt=r_prompt,
                style=style,
                set_exception_handler=False,
            )
        except KeyboardInterrupt:
            self.stop()
            raise

    async def loop(self) -> None:
        """Console 的输入循环"""
        from graia.ariadne.message.chain import MessageChain
        from graia.ariadne.message.element import Plain

        class _Dispatcher(BaseDispatcher):
            def __init__(self, command: str, console: Console) -> None:
                self.command = command
                self.console = console

            async def catch(self, interface: DispatcherInterface):
                if interface.annotation is str and interface.name == "command":
                    return self.command
                if interface.annotation is MessageChain:
                    return MessageChain([Plain(self.command)], inline=True)
                if interface.annotation is Console:
                    return self.console
                if interface.annotation is Broadcast:
                    return self.console.broadcast
                if interface.annotation is AbstractEventLoop:
                    return self.console.broadcast.loop

        while self.running:
            try:
                command = await self.prompt()
            except KeyboardInterrupt:
                self.stop()
                raise
            for func, dispatchers, decorators in self.registry:
                try:
                    result = await self.broadcast.Executor(
                        ExecTarget(
                            func,
                            resolve_dispatchers_mixin(
                                [_Dispatcher(command, self), ContextDispatcher(), *dispatchers]
                            ),
                            decorators,
                        ),
                    )
                except DisabledNamespace as e:
                    logger.exception(e)
                except PropagationCancelled:
                    break
                except Exception:
                    pass
                else:
                    if isinstance(result, str):
                        logger.info(result)
                    elif isinstance(result, MessageChain):
                        logger.info(result.display)

    def start(self):
        """启动 Console, 幂等"""
        if not self.running:
            self.running = True

            if self.replace_logger:
                with contextlib.suppress(ValueError):
                    logger.remove(0)
                self.handler_id = logger.add(StdoutProxy(raw=True))  # type: ignore

            self.task = self.broadcast.loop.create_task(self.loop())

    def stop(self):
        """提示 Console 停止, 非异步, 幂等"""

        if self.running:
            logger.info("Stopping console...")

            self.running = False

            if self.replace_logger:
                logger.remove(self.handler_id)
                self.handler_id = logger.add(sys.stderr)

    async def join(self):
        """等待 Console 结束, 异步, 幂等"""
        if self.task:
            await self.task
            self.task = None

    def register(
        self,
        dispatchers: Optional[List[BaseDispatcher]] = None,
        decorators: Optional[List[Decorator]] = None,
    ):
        """注册命令处理函数

        Args:
            dispatchers (List[BaseDispatcher], optional): 使用的 Dispatcher 列表.
            decorators (List[Decorator], optional): 使用的 Decorator 列表.
        """

        def wrapper(func: Callable):
            self.registry.append((func, dispatchers or [], decorators or []))
            return func

        return wrapper
