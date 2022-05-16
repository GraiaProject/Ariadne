import asyncio
from typing import Any, Awaitable, Callable, Dict, List, MutableSet, Optional

from graia.amnesia.builtins.aiohttp import AiohttpClientInterface
from graia.amnesia.launch.component import LaunchComponent
from graia.amnesia.launch.interface import ExportInterface
from graia.amnesia.launch.manager import LaunchManager
from graia.amnesia.launch.service import Service
from typing_extensions import Self

from ..event.mirai import MiraiEvent
from .config import HttpClientConfig, U_Config
from .connection import (
    CONFIG_MAP,
    ConnectionMixin,
    ConnectionStatus,
    HttpClientConnection,
)
from .util import CallMethod as CallMethod  # noqa: F401


class ConnectionInterface(ExportInterface["ElizabethConnectionService"]):
    service: "ElizabethConnectionService"
    connection: Optional[ConnectionMixin]

    def __init__(self, service: "ElizabethConnectionService") -> None:
        self.service = service
        self.connection = None

    def bind(self, account: int) -> Self:
        if account not in self.service.connections:
            raise ValueError(f"Account {account} not found")
        self.connection = self.service.connections[account]
        return self

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
    http_interface: AiohttpClientInterface

    def __init__(self, configs: List[U_Config]) -> None:
        self.connections: Dict[int, ConnectionMixin] = {}
        self.event_callbacks: Dict[int, List[Callable[["MiraiEvent"], Awaitable[Any]]]] = {}
        conf_map: Dict[int, List[U_Config]] = {}
        for conf in configs:
            conf_map.setdefault(conf.account, []).append(conf)
        for configs in conf_map.values():
            configs.sort(key=lambda x: isinstance(x, HttpClientConfig))
            # make sure the http client is the last one
            for conf in configs:
                self.update_from_config(conf)

    def update_from_config(self, config: U_Config) -> None:
        account: int = config.account
        connection = CONFIG_MAP[config.__class__](config)
        if account not in self.connections:
            self.connections[account] = connection
        elif isinstance(connection, HttpClientConnection):
            upstream_conn = self.connections[account]
            if upstream_conn.fallback:
                raise ValueError(f"{upstream_conn} already has fallback connection")
            connection.status = upstream_conn.status
            upstream_conn.fallback = connection
        else:
            raise ValueError(f"Connection {self.connections[account]} conflicts with {connection}")

    async def connection_daemon(self, connection: ConnectionMixin, mgr: LaunchManager) -> None:
        connection.http_interface = self.http_interface
        if connection.fallback:
            connection.fallback.http_interface = self.http_interface
            connection.fallback.status = connection.status
        await connection.mainline(mgr)  # TODO: auto reboot

    async def mainline(self, mgr: LaunchManager) -> None:
        self.http_interface = mgr.get_interface(AiohttpClientInterface)
        await asyncio.wait(
            [asyncio.create_task(self.connection_daemon(conn, mgr)) for conn in self.connections.values()]
        )

    @property
    def launch_component(self) -> LaunchComponent:
        requirements: MutableSet[str] = set()
        for connection in self.connections.values():
            requirements |= connection.dependencies
        return LaunchComponent("elizabeth.connection", requirements, self.mainline)

    def get_interface(self, interface_type: type):
        if interface_type is ConnectionInterface:
            return ConnectionInterface(self)
