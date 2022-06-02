import asyncio
import contextlib
from typing import (
    Dict,
    Iterable,
    MutableMapping,
    MutableSet,
    Optional,
    Tuple,
    Type,
    overload,
)
from weakref import WeakValueDictionary

from graia.amnesia.builtins.aiohttp import AiohttpClientInterface
from graia.broadcast import Broadcast
from launart import Launart, Service
from loguru import logger
from typing_extensions import Self

from .connection import (
    CONFIG_MAP,
    ConnectionInterface,
    ConnectionMixin,
    HttpClientConnection,
)
from .connection._info import HttpClientInfo, T_Info, U_Info
from .dispatcher import ContextDispatcher, NoneDispatcher


class ElizabethService(Service):
    id = "elizabeth.service"
    supported_interface_types = {ConnectionInterface}
    http_interface: AiohttpClientInterface
    connections: Dict[int, ConnectionMixin]
    broadcast: Broadcast
    connection_tasks: MutableMapping[int, asyncio.Task]

    def __init__(self, broadcast: Optional[Broadcast] = None) -> None:
        super().__init__()
        self.connections = {}
        self.connection_tasks = WeakValueDictionary()
        self.broadcast = broadcast or Broadcast(loop=asyncio.new_event_loop())
        asyncio.set_event_loop(self.broadcast.loop)
        if ContextDispatcher not in self.broadcast.prelude_dispatchers:
            self.broadcast.prelude_dispatchers.append(ContextDispatcher)
        if NoneDispatcher not in self.broadcast.finale_dispatchers:
            self.broadcast.finale_dispatchers.append(NoneDispatcher)

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

    async def connection_daemon(self, connection: ConnectionMixin[T_Info], mgr: Launart) -> None:
        from .app import Ariadne
        from .context import enter_context
        from .event.lifecycle import AccountLaunch

        account = connection.config.account

        connection.http_interface = self.http_interface
        if connection.fallback:
            connection.fallback.http_interface = self.http_interface
            connection.fallback.status = connection.status
        logger.info(
            f"Establishing connection {connection}",
            alt=f"[green]Establishing connection[/green] {connection}",
        )
        app: Ariadne = Ariadne.current(account)
        conn_task = asyncio.create_task(connection.mainline(mgr))
        self.connection_tasks[account] = conn_task
        with enter_context(app=app):
            self.broadcast.postEvent(AccountLaunch(app))
        with contextlib.suppress(asyncio.CancelledError):
            await conn_task

    async def prepare(self, mgr: Launart) -> None:
        self.http_interface = mgr.get_interface(AiohttpClientInterface)
        if self.broadcast:
            assert asyncio.get_running_loop() is self.loop, "Broadcast is attached to a different loop"
        else:
            self.broadcast = Broadcast(loop=asyncio.get_running_loop())

    async def cleanup(self) -> None:
        from .app import Ariadne
        from .context import enter_context
        from .event.lifecycle import AccountShutdown

        logger.info("Elizabeth Service cleaning up...", style="orange")
        for account in self.connections:
            app: Ariadne = Ariadne.current(account)
            task = self.connection_tasks.pop(account, None)
            if task:
                with enter_context(app=app):
                    await self.broadcast.postEvent(AccountShutdown(app))
                if not task.done():
                    task.cancel()

    async def launch(self, manager: Launart):
        from .app import Ariadne
        from .event.lifecycle import ApplicationLaunched, ApplicationShutdowned

        while self.status.stage != "prepare":
            await self.status.wait_for_update()
        await self.prepare(manager)
        if "default_account" in Ariadne.options:
            self.broadcast.postEvent(ApplicationLaunched(Ariadne.current()))
        tasks = [
            asyncio.create_task(self.connection_daemon(conn, manager)) for conn in self.connections.values()
        ]
        self.status.set_blocking()
        await manager.status.wait_for_completed()
        self.status.set_cleanup()
        if "default_account" in Ariadne.options:
            self.broadcast.postEvent(ApplicationShutdowned(Ariadne.current()))
        await self.cleanup()
        for task in tasks:
            if not task.done():
                task.cancel()
        logger.success(f"Cancelled {len(tasks)} connection tasks", style="green")
        self.status.set_finished()

    @property
    def required(self):
        requirements: MutableSet[str] = set()
        for connection in self.connections.values():
            requirements |= connection.dependencies
        return requirements

    def on_require_prepared(self, _):
        self.status.set_prepare()

    @property
    def stages(self):
        return {"prepare", "blocking", "cleanup"}

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
