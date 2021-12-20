import importlib.metadata
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from graia.broadcast import Broadcast
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.exectarget import ExecTarget
from graia.broadcast.exceptions import DisabledNamespace, PropagationCancelled
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from loguru import logger
from prompt_toolkit import HTML, PromptSession

from graia.ariadne.util import yield_with_timeout


class Console:
    def __init__(
        self,
        broadcast: Broadcast,
        *,
        bg: Optional[str] = None,
        fg: str = "blue",
        prompt: str = "{library_name} {graia_ariadne_version}>",
        extra_data_getter: Iterable[Callable[[], Dict[str, Any]]] = (),
    ) -> None:
        self.broadcast = broadcast

        style = [f'bg="{bg}"' if bg else "", f'fg="{fg}"' if fg else ""]
        self.session: PromptSession[str] = PromptSession()

        self.style = f'<style {" ".join(style)}>{prompt}</style>'

        self.registry: List[Tuple[Callable, List[BaseDispatcher], List[Decorator]]] = []
        self.extra_data_getter = extra_data_getter

        self.running: bool = False

    def data_getter(self) -> Dict[str, Any]:

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

    async def loop(self):
        from graia.ariadne.message.chain import MessageChain
        from graia.ariadne.message.element import Plain

        class _Dispatcher(BaseDispatcher):
            def __init__(self, command: str) -> None:
                self.command = command

            async def catch(self, interface: DispatcherInterface):
                if interface.annotation is str and interface.name == "command":
                    return self.command
                elif interface.annotation is MessageChain:
                    return MessageChain([Plain(self.command)], inline=True)

        async for command in yield_with_timeout(
            lambda: self.session.prompt_async(message=HTML(self.style.format_map(self.data_getter()))),
            lambda: self.running,
        ):

            for func, dispatchers, decorators in self.registry:
                try:
                    result = await self.broadcast.Executor(
                        ExecTarget(func, [_Dispatcher(command)] + dispatchers), decorators
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
                        logger.info(result.asDisplay())

    def start(self):
        self.running = True
        self.task = self.broadcast.loop.create_task(self.loop())

    def stop(self):
        self.running = False

    async def join(self):
        await self.task
        self.task = None

    def register(self, dispatchers: List[BaseDispatcher] = None, decorators: List[Decorator] = None):
        def wrapper(func: Callable):
            self.registry.append((func, dispatchers or [], decorators or []))
            return func

        return wrapper
