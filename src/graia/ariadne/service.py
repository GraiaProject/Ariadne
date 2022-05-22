import asyncio
import contextlib
from typing import Dict, Iterable, MutableMapping, MutableSet, Tuple, Type, overload
from weakref import WeakValueDictionary

from graia.amnesia.builtins.aiohttp import AiohttpClientInterface
from graia.amnesia.launch.component import LaunchComponent
from graia.amnesia.launch.manager import LaunchManager
from graia.amnesia.launch.service import Service
from graia.broadcast import Broadcast
from loguru import logger
from typing_extensions import Self

from .connection import (
    CONFIG_MAP,
    ConnectionInterface,
    ConnectionMixin,
    HttpClientConnection,
)
from .connection._info import HttpClientInfo, T_Info, U_Info
from .dispatcher import ContextDispatcher


class ElizabethService(Service):
    supported_interface_types = {ConnectionInterface}
    http_interface: AiohttpClientInterface
    connections: Dict[int, ConnectionMixin]
    broadcast: Broadcast
    connection_tasks: MutableMapping[int, asyncio.Task]

    def __init__(self) -> None:
        self.connections = {}
        self.connection_tasks = WeakValueDictionary()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.broadcast = Broadcast(loop=loop)
        self.broadcast.prelude_dispatchers.append(ContextDispatcher)

    def add_configs(self, configs: Iterable[U_Info]) -> Tuple[Self, int]:
        configs = list(configs)
        assert configs
        account: int = configs[0].account
        assert account not in self.connections, f"Account {account} already exists"
        assert all(
            conf.account == account for conf in configs
        ), f"All configs must be for the account {account}"
        configs.sort(key=lambda x: isinstance(x, HttpClientInfo))
        # make sure the http client is the last one
        for conf in configs:
            self.update_from_config(conf)
        return self, account

    def update_from_config(self, config: U_Info) -> None:
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

    async def connection_daemon(self, connection: ConnectionMixin[T_Info], mgr: LaunchManager) -> None:
        from .app import Ariadne
        from .context import enter_context
        from .event.lifecycle import ApplicationLaunched

        account = connection.config.account

        connection.http_interface = self.http_interface
        if connection.fallback:
            connection.fallback.http_interface = self.http_interface
            connection.fallback.status = connection.status
        logger.info(
            f"Establishing connection {connection}",
            alt=f"[green]Establishing connection[/green] {connection}",
        )
        app: Ariadne = Ariadne(account)
        with enter_context(app=app):
            self.broadcast.postEvent(ApplicationLaunched(app))
        conn_task = asyncio.create_task(connection.mainline(mgr))
        self.connection_tasks[account] = conn_task
        with contextlib.suppress(asyncio.CancelledError):
            await conn_task

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

    async def cleanup(self, mgr: LaunchManager) -> None:
        from .app import Ariadne
        from .context import enter_context
        from .event.lifecycle import ApplicationShutdowned

        for account in self.connections:
            app: Ariadne = Ariadne(account)
            with enter_context(app=app):
                await self.broadcast.postEvent(ApplicationShutdowned(app))
            task = self.connection_tasks.pop(account, None)
            if task and not task.done():
                task.cancel()

    @property
    def launch_component(self) -> LaunchComponent:
        requirements: MutableSet[str] = set()
        for connection in self.connections.values():
            requirements |= connection.dependencies
        return LaunchComponent("elizabeth.service", requirements, self.mainline, self.prepare, self.cleanup)

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self.broadcast.loop

    @overload
    def get_interface(self, interface_type: Type[ConnectionInterface]) -> ConnectionInterface:
        ...

    @overload
    def get_interface(self, interface_type: type) -> None:
        ...

    def get_interface(self, interface_type: type):
        if interface_type is ConnectionInterface:
            return ConnectionInterface(self)
