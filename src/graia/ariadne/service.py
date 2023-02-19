"""Ariadne 的 launart 服务相关"""
import asyncio
import importlib.metadata
import json
from typing import Coroutine, Dict, Iterable, List, Tuple, Type, overload

from aiohttp import ClientSession
from launart import Launart, Service
from loguru import logger
from packaging.version import Version

from graia.amnesia.builtins.aiohttp import AiohttpClientInterface
from graia.broadcast import Broadcast

from .connection import CONFIG_MAP, ConnectionInterface, ConnectionMixin, HttpClientConnection
from .connection._info import HttpClientInfo, U_Info
from .dispatcher import ContextDispatcher, LaunartInterfaceDispatcher, NoneDispatcher
from .exception import AriadneConfigurationError

ARIADNE_ASCII_LOGO = r"""
    _         _           _
   / \   _ __(_) __ _  __| |_ __   ___
  / _ \ | '__| |/ _` |/ _` | '_ \ / _ \
 / ___ \| |  | | (_| | (_| | | | |  __/
/_/   \_\_|  |_|\__,_|\__,_|_| |_|\___|"""

monitored_prefix = ("kayaku", "statv", "launart", "luma", "graia", "avilla")


async def check_update(session: ClientSession, name: str, current: str, output: List[str]) -> None:
    """在线检查更新"""
    result: str = current
    result_version = current_version = Version(current)
    try:
        async with session.get(f"http://mirrors.aliyun.com/pypi/web/json/{name}") as resp:
            data = await resp.text()
            result: str = json.loads(data)["info"]["version"]
            result_version = Version(result)
    except Exception as e:
        logger.warning(f"Failed to retrieve latest version of {name}: {e}")
    if result_version > current_version:
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
    """获取与项目相关的发行字典"""
    dist_map: dict[str, str] = {}
    for dist in importlib.metadata.distributions():
        name: str = dist.metadata["Name"]
        version: str = dist.metadata["Version"]
        if not name or not version:
            continue
        if name.startswith(monitored_prefix):
            dist_map[name] = max(version, dist_map.get(name, ""))
    return dist_map


class ElizabethService(Service):
    """ElizabethService, Ariadne 的直接后端"""

    id = "elizabeth.service"
    supported_interface_types = {ConnectionInterface}
    http_interface: AiohttpClientInterface
    connections: Dict[int, ConnectionMixin[U_Info]]
    broadcast: Broadcast

    def __init__(self) -> None:
        """初始化 ElizabethService"""
        import creart

        self.connections = {}
        self.broadcast = creart.it(Broadcast)

        if ContextDispatcher not in self.broadcast.prelude_dispatchers:
            self.broadcast.prelude_dispatchers.append(ContextDispatcher)
        if LaunartInterfaceDispatcher not in self.broadcast.prelude_dispatchers:
            self.broadcast.prelude_dispatchers.append(LaunartInterfaceDispatcher)
        if NoneDispatcher not in self.broadcast.finale_dispatchers:
            self.broadcast.finale_dispatchers.append(NoneDispatcher)

        super().__init__()

    @staticmethod
    def base_telemetry() -> None:
        """执行基础遥测检查"""
        output: List[str] = [""]
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
        output.insert(0, f"[cyan]{ARIADNE_ASCII_LOGO}[/]")
        rich_output = "\n".join(output)
        logger.opt(colors=True).info(
            rich_output.replace("[", "<").replace("]", ">"), alt=rich_output, highlighter=None
        )

    @staticmethod
    async def check_update() -> None:
        """执行更新检查"""
        output: List[str] = []
        dist_map: Dict[str, str] = get_dist_map()
        async with ClientSession() as session:
            await asyncio.gather(
                *(check_update(session, name, version, output) for name, version in dist_map.items())
            )
        output.sort()
        if output:
            output = (
                ["", "[bold]", f"[red]{len(output)}[/] [yellow]update(s) available:[/]"] + output + ["[/]"]
            )
            rich_output = "\n".join(output)
            logger.opt(colors=True).warning(
                rich_output.replace("[", "<").replace("]", ">"), alt=rich_output, highlighter=None
            )
        else:
            logger.opt(colors=True).success("All dependencies up to date!", style="green")

    def add_infos(self, infos: Iterable[U_Info]) -> Tuple[List[ConnectionMixin], int]:
        """通过传入的 Info 对象创建 Connection"""
        infos = list(infos)
        if not infos:
            raise AriadneConfigurationError("No configs provided")

        account: int = infos[0].account
        if account in self.connections:
            raise AriadneConfigurationError(f"Account {account} already exists")
        if len({i.account for i in infos}) != 1:
            raise AriadneConfigurationError("All configs must be for the same account")

        infos.sort(key=lambda x: isinstance(x, HttpClientInfo))
        # make sure the http client is the last one
        conns: List[ConnectionMixin] = [self.add_info(conf) for conf in infos]
        return conns, account

    def add_info(self, config: U_Info) -> ConnectionMixin:
        """添加单个 Info"""
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
        """Launart 启动点"""
        from .app import Ariadne
        from .context import enter_context
        from .event.lifecycle import AccountLaunch, AccountShutdown, ApplicationLaunch, ApplicationShutdown

        self.base_telemetry()
        async with self.stage("preparing"):
            self.http_interface = mgr.get_interface(AiohttpClientInterface)
            if "default_account" in Ariadne.options:
                app = Ariadne.current()
                with enter_context(app=app):
                    self.broadcast.postEvent(ApplicationLaunch(app))
            for conn in self.connections.values():
                app = Ariadne.current(conn.info.account)

                def _disconnect_cb():
                    from graia.ariadne.event.lifecycle import AccountConnectionFail

                    self.broadcast.postEvent(AccountConnectionFail(app))

                conn._connection_fail = _disconnect_cb

                with enter_context(app=app):
                    self.broadcast.postEvent(AccountLaunch(app))

        async with self.stage("cleanup"):
            logger.info("Elizabeth Service cleaning up...", style="dark_orange")
            if "default_account" in Ariadne.options:
                app = Ariadne.current()
                if app.connection.status.available:
                    with enter_context(app=app):
                        await self.broadcast.postEvent(ApplicationShutdown(app))
            for conn in self.connections.values():
                if conn.status.available:
                    app = Ariadne.current(conn.info.account)
                    with enter_context(app=app):
                        await self.broadcast.postEvent(AccountShutdown(app))

            for task in asyncio.all_tasks():
                if task.done():
                    continue
                coro: Coroutine = task.get_coro()  # type: ignore
                if coro.__qualname__ == "Broadcast.Executor":
                    task.cancel()
                    logger.debug(f"Cancelled {task.get_name()} (Broadcast.Executor)")

            logger.info("Checking for updates...", alt="[cyan]Checking for updates...[/]")
            await self.check_update()

    @property
    def client_session(self) -> ClientSession:
        """获取 aiohttp 的 ClientSession

        Returns:
            ClientSession: ClientSession 对象
        """
        return self.http_interface.service.session

    @property
    def required(self):
        dependencies = {AiohttpClientInterface}
        for conn in self.connections.values():
            dependencies |= conn.dependencies
            dependencies.add(conn.id)
        return dependencies

    @property
    def stages(self):
        return {"preparing", "cleanup"}

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """获取绑定的事件循环

        Returns:
            asyncio.AbstractEventLoop: 事件循环
        """
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
