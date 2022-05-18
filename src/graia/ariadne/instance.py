import asyncio
from typing import Callable, ClassVar, Iterable, Optional, Union

from graia.amnesia.launch.manager import LaunchManager

from .connection import ConnectionMixin
from .connection.config import U_Config
from .model import LogConfig
from .service import ElizabethService


class Ariadne:
    service: ClassVar[ElizabethService] = ElizabethService()
    launch_manager: ClassVar[LaunchManager] = LaunchManager()

    def __init__(
        self,
        connection: Union[Iterable[U_Config], int] = (),
        log_config: Optional[LogConfig] = None,
    ) -> None:
        if isinstance(connection, Iterable):
            account = Ariadne.service.add_configs(connection)[1]
        else:
            account = connection
        self.account: int = account
        self.connection: ConnectionMixin = Ariadne.service.connections[account]
        self.log_config: LogConfig = log_config or LogConfig()
        self.connection.event_callbacks.append(self.log_config.event_hook(self))

    @classmethod
    async def launch(cls) -> None:
        assert asyncio.get_running_loop() is cls.service.loop, "ElizabethService attached to different loop"
        await cls.launch_manager.launch()

    @classmethod
    def launch_blocking(cls):
        cls.launch_manager.launch_blocking(loop=cls.service.loop)

    def __getattr__(self, snake_case_name: str) -> Callable:
        # snake_case to camelCase
        snake_segments = snake_case_name.split("_")
        camel_case_name = snake_segments[0] + "".join(s.capitalize() for s in snake_segments[1:])
        return self.__dict__[camel_case_name]
