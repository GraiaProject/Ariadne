import asyncio
from typing import Dict, Iterable, List, Optional, Tuple, Type, overload

from graia.amnesia.builtins.aiohttp import AiohttpClientInterface
from graia.broadcast import Broadcast
from launart import Service
from loguru import logger

from graia.ariadne.exception import AriadneConfigurationError

from .connection import (
    CONFIG_MAP,
    ConnectionInterface,
    ConnectionMixin,
    HttpClientConnection,
)
from .connection._info import HttpClientInfo, U_Info
from .dispatcher import ContextDispatcher, NoneDispatcher


class ElizabethService(Service):
    id = "elizabeth.service"
    supported_interface_types = {ConnectionInterface}
    http_interface: AiohttpClientInterface
    connections: Dict[int, ConnectionMixin[U_Info]]
    broadcast: Broadcast

    def __init__(self, broadcast: Optional[Broadcast] = None) -> None:
        self.connections = {}
        self.broadcast = broadcast or Broadcast(loop=asyncio.new_event_loop())

        asyncio.set_event_loop(self.broadcast.loop)

        if ContextDispatcher not in self.broadcast.prelude_dispatchers:
            self.broadcast.prelude_dispatchers.append(ContextDispatcher)
        if NoneDispatcher not in self.broadcast.finale_dispatchers:
            self.broadcast.finale_dispatchers.append(NoneDispatcher)

        super().__init__()

    def add_configs(self, configs: Iterable[U_Info]) -> Tuple[List[ConnectionMixin], int]:
        configs = list(configs)
        if not configs:
            raise AriadneConfigurationError("No configs provided")

        account: int = configs[0].account
        if account in self.connections:
            raise AriadneConfigurationError(f"Account {account} already exists")
        if len({i.account for i in configs}) != 1:
            raise AriadneConfigurationError("All configs must be for the same account")

        configs.sort(key=lambda x: isinstance(x, HttpClientInfo))
        # make sure the http client is the last one
        conns: List[ConnectionMixin] = [self.add_info(conf) for conf in configs]
        return conns, account

    def add_info(self, config: U_Info) -> ConnectionMixin:
        account: int = config.account
        connection = CONFIG_MAP[config.__class__](config)
        if account not in self.connections:
            self.connections[account] = connection
        elif isinstance(connection, HttpClientConnection):
            upstream_conn = self.connections[account]
            if upstream_conn.fallback:
                raise ValueError(f"{upstream_conn} already has fallback connection")
            connection.status = upstream_conn.status
            connection.is_hook = True
            upstream_conn.fallback = connection
        else:
            raise ValueError(f"Connection {self.connections[account]} conflicts with {connection}")
        return connection

    async def launch(self, _):
        from .app import Ariadne
        from .context import enter_context
        from .event.lifecycle import (
            AccountLaunch,
            AccountShutdown,
            ApplicationLaunched,
            ApplicationShutdowned,
        )

        async with self.stage("preparing"):
            if self.broadcast:
                if asyncio.get_running_loop() is not self.loop:
                    raise AriadneConfigurationError("Broadcast is attached to a different loop")
            else:
                self.broadcast = Broadcast(loop=self.loop)
            if "default_account" in Ariadne.options:
                app = Ariadne.current()
                with enter_context(app=app):
                    self.broadcast.postEvent(ApplicationLaunched(app))
            for conn in self.connections.values():
                app = Ariadne.current(conn.config.account)
                with enter_context(app=app):
                    self.broadcast.postEvent(AccountLaunch(app))

        async with self.stage("cleanup"):
            logger.info("Elizabeth Service cleaning up...", style="dark_orange")
            if "default_account" in Ariadne.options:
                app = Ariadne.current()
                with enter_context(app=app):
                    await self.broadcast.postEvent(ApplicationShutdowned(app))
            for conn in self.connections.values():
                if conn.status.available:
                    app = Ariadne.current(conn.config.account)
                    with enter_context(app=app):
                        await self.broadcast.postEvent(AccountShutdown(app))

    @property
    def required(self):
        return {conn.id for conn in self.connections.values()}

    @property
    def stages(self):
        return {"preparing", "cleanup"}

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
