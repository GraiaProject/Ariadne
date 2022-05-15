import asyncio
from typing import Any, Awaitable, Callable, Dict, List, MutableSet, Optional

from graia.amnesia.launch.component import LaunchComponent
from graia.amnesia.launch.interface import ExportInterface
from graia.amnesia.launch.manager import LaunchManager
from graia.amnesia.launch.service import Service

from ..event.mirai import MiraiEvent
from .config import U_Config
from .connection import CONFIG_MAP, ConnectionStatus, ConnectionMixin, HttpClientConnection
from .util import CallMethod as CallMethod  # noqa: F401


class ConnectionInterface(ExportInterface["ElizabethConnectionService"]):
    service: "ElizabethConnectionService"
    connection: Optional[ConnectionMixin]

    def __init__(self, service: "ElizabethConnectionService") -> None:
        self.service = service

    def bind(self, account: int) -> None:
        if account not in self.service.connections:
            raise ValueError(f"Account {account} not found")
        self.connection = self.service.connections[account]

    async def call(
        self, method: CallMethod, command: str, params: dict, *, account: Optional[int] = None
    ) -> Any:
        connection = self.connection
        if account is not None:
            connection = self.service.connections.get(account)
        if connection is None:
            raise ValueError(f"Unable to find connection to execute {command}")
        return await connection.call(method, command, params)

    def add_callback(self, callback: Callable[[MiraiEvent], Awaitable[Any]]) -> None:
        if self.connection is None:
            raise ValueError("Unable to find connection to add callback")
        self.connection.event_callbacks.append(callback)

    @property
    def status(self) -> ConnectionStatus:
        if self.connection:
            return self.connection.status
        raise ValueError(f"{self} is not bound to an account")


class ElizabethConnectionService(Service):
    supported_interface_types = {ConnectionInterface}

    def __init__(self, configs: List[U_Config]) -> None:
        self.connections: Dict[int, ConnectionMixin] = {}
        self.event_callbacks: Dict[int, List[Callable[["MiraiEvent"], Awaitable[Any]]]] = {}
        conf_map: Dict[int, List[U_Config]] = {}
        for conf in configs:
            conf_map.setdefault(conf.account, []).append(conf)
        for configs in conf_map.values():
            configs.sort(key=lambda x: isinstance(x, HttpClientConnection))
            # make sure the http client is the last one
            for conf in configs:
                self.update_from_config(conf)

    def update_from_config(self, config: U_Config) -> None:
        account: int = config.account
        connection = CONFIG_MAP[config.__class__](config)
        if account not in self.connections:
            self.connections[account] = connection
        elif isinstance(connection, HttpClientConnection):
            connection.hook(self.connections[account])
        else:
            raise ValueError(
                f"{account} already has connection {self.connections[account]}, found {connection}"
            )

    async def mainline(self, mgr: LaunchManager) -> None:
        await asyncio.wait(
            [asyncio.create_task(connection.mainline(mgr)) for connection in self.connections.values()]
        )

    @property
    def launch_component(self) -> LaunchComponent:
        requirements: MutableSet[str] = set()
        for connection in self.connections.values():
            requirements.update(connection.dependencies)
        return LaunchComponent("elizabeth.connection", requirements, self.mainline)

    def get_interface(self, interface_type: type):
        if interface_type is ConnectionInterface:
            return ConnectionInterface(self)
