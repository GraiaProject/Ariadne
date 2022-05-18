import asyncio
from typing import Dict, Iterable, MutableSet, Tuple

from graia.amnesia.builtins.aiohttp import AiohttpClientInterface
from graia.amnesia.launch.component import LaunchComponent
from graia.amnesia.launch.manager import LaunchManager
from graia.amnesia.launch.service import Service
from graia.broadcast import Broadcast
from typing_extensions import Self

from .connection import (
    CONFIG_MAP,
    ConnectionInterface,
    ConnectionMixin,
    HttpClientConnection,
)
from .connection.config import HttpClientConfig, U_Config


class ElizabethService(Service):
    supported_interface_types = {ConnectionInterface}
    http_interface: AiohttpClientInterface
    connections: Dict[int, ConnectionMixin]
    broadcast: Broadcast

    def __init__(self) -> None:
        self.connections = {}
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.broadcast = Broadcast(loop=loop)

    def add_configs(self, configs: Iterable[U_Config]) -> Tuple[Self, int]:
        configs = list(configs)
        assert configs
        account: int = configs[0].account
        assert account not in self.connections, f"Account {account} already exists"
        assert all(
            conf.account == account for conf in configs
        ), f"All configs must be for the account {account}"
        configs.sort(key=lambda x: isinstance(x, HttpClientConfig))
        # make sure the http client is the last one
        for conf in configs:
            self.update_from_config(conf)
        return self, account

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

    async def prepare(self, mgr: LaunchManager) -> None:
        self.http_interface = mgr.get_interface(AiohttpClientInterface)
        if self.broadcast:
            assert asyncio.get_running_loop() is self.loop, "Broadcast is attached to a different loop"
        else:
            self.broadcast = Broadcast(loop=asyncio.get_running_loop())

    async def mainline(self, mgr: LaunchManager) -> None:
        await asyncio.wait(
            [asyncio.create_task(self.connection_daemon(conn, mgr)) for conn in self.connections.values()]
        )

    @property
    def launch_component(self) -> LaunchComponent:
        requirements: MutableSet[str] = set()
        for connection in self.connections.values():
            requirements |= connection.dependencies
        return LaunchComponent("elizabeth.service", requirements, self.mainline, self.prepare)

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self.broadcast.loop

    def get_interface(self, interface_type: type):
        if interface_type is ConnectionInterface:
            return ConnectionInterface(self)
