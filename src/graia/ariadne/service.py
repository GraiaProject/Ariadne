import asyncio
import importlib.metadata
import json
from typing import Coroutine, Dict, Iterable, List, Optional, Tuple, Type, overload

from aiohttp import ClientSession
from graia.amnesia.builtins.aiohttp import AiohttpClientInterface
from graia.broadcast import Broadcast
from launart import Launart, Service
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

ARIADNE_ASCII_LOGO = r"""
    _         _           _
   / \   _ __(_) __ _  __| |_ __   ___
  / _ \ | '__| |/ _` |/ _` | '_ \ / _ \
 / ___ \| |  | | (_| | (_| | | | |  __/
/_/   \_\_|  |_|\__,_|\__,_|_| |_|\___|"""


async def check_update(session: ClientSession, name: str, current: str, output: List[str]) -> None:
    try:
        async with session.get(f"https://mirrors.aliyun.com/pypi/web/json/{name}") as resp:
            data = await resp.text()
            result: str = json.loads(data)["info"]["version"]
    except Exception as e:
        logger.warning(f"Failed to retrieve latest version of {name}: {e}")
        result: str = current
    if result > current:
        output.append(
            " ".join(
                [
                    f"[cyan]{name}[/]:" if name.startswith("graiax-") else f"[magenta]{name}[/]:",
                    f"[green]{current}[/]",
                    f"-> [yellow]{result}[/]",
                ]
            )
        )


def get_dist_map() -> Dict[str, str]:
    dist_map: Dict[str, str] = {}
    for dist in importlib.metadata.distributions():
        name: str = dist.metadata["Name"]
        version: str = dist.version
        if name.startswith("graia-") or name.startswith("graiax-"):
            dist_map[name] = max(version, dist_map.get(name, ""))
    return dist_map


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

    @staticmethod
    def base_telemetry() -> None:
        output: List[str] = [f"[cyan]{ARIADNE_ASCII_LOGO}[/]"]
        dist_map: Dict[str, str] = get_dist_map()
        output.extend(
            " ".join(
                [
                    f"[blue]{name}[/]:" if name.startswith("graiax-") else f"[magenta]{name}[/]:",
                    f"[green]{version}[/]",
                ]
            )
            for name, version in dist_map.items()
        )
        output.sort()
        rich_output = "\n".join(output)
        logger.opt(colors=True).info(
            rich_output.replace("[", "<").replace("]", ">"), alt=rich_output, highlighter=None
        )

    @staticmethod
    async def check_update() -> None:
        output: List[str] = []
        dist_map: Dict[str, str] = get_dist_map()
        async with ClientSession() as session:
            await asyncio.gather(
                *(check_update(session, name, version, output) for name, version in dist_map.items())
            )
        output.sort()
        if output:
            output = ["[bold]", f"[red]{len(output)}[/] [yellow]update(s) available:[/]"] + output + ["[/]"]
        rich_output = "\n".join(output)
        logger.opt(colors=True).warning(
            rich_output.replace("[", "<").replace("]", ">"), alt=rich_output, highlighter=None
        )

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

    async def launch(self, mgr: Launart):
        from .app import Ariadne
        from .context import enter_context
        from .event.lifecycle import (
            AccountLaunch,
            AccountShutdown,
            ApplicationLaunched,
            ApplicationShutdowned,
        )

        self.base_telemetry()
        async with self.stage("preparing"):
            self.http_interface = mgr.get_interface(AiohttpClientInterface)
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

            for task in asyncio.all_tasks():
                if task.done():
                    continue
                coro: Coroutine = task.get_coro()  # type: ignore
                if coro.__qualname__ == "Broadcast.Executor":
                    task.cancel()
                    logger.debug(f"Cancelling {task.get_name()} (Broadcast.Executor)")
                elif coro.cr_frame.f_globals["__name__"].startswith("graia.scheduler"):
                    task.cancel()
                    logger.debug(f"Cancelling {task.get_name()} (Scheduler Task)")

            logger.info("Checking for updates...")
            await self.check_update()

    @property
    def client_session(self) -> ClientSession:
        return self.http_interface.service.session

    @property
    def required(self):
        return {"http.universal_client"} | {conn.id for conn in self.connections.values()}

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
