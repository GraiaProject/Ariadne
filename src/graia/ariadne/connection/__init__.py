import asyncio
from typing import Any, Awaitable, Callable, Dict, List, MutableSet, Optional

from graia.amnesia.launch.component import LaunchComponent
from graia.amnesia.launch.interface import ExportInterface
from graia.amnesia.launch.manager import LaunchManager
from graia.amnesia.launch.service import Service

from ..event.mirai import MiraiEvent
from .config import ConfigUnion
from .connector import CONFIG_MAP, ConnectionStatus, ConnectorMixin, HttpClientConnector
from .util import CallMethod as CallMethod  # noqa: F401


class ConnectionInterface(ExportInterface["ConnectionService"]):
    service: "ConnectionService"
    connector: Optional[ConnectorMixin]

    def __init__(self, service: "ConnectionService") -> None:
        self.service = service

    def bind(self, account: int) -> None:
        if account not in self.service.connections:
            raise ValueError(f"Account {account} not found")
        self.connector = self.service.connections[account]

    async def call(
        self, method: CallMethod, command: str, params: dict, *, account: Optional[int] = None
    ) -> Any:
        connector = self.connector
        if account is not None:
            connector = self.service.connections.get(account)
        if connector is None:
            raise ValueError(f"Unable to find connection to execute {command}")
        return await connector.call(method, command, params)

    def add_callback(self, callback: Callable[[MiraiEvent], Awaitable[Any]]) -> None:
        if self.connector is None:
            raise ValueError("Unable to find connection to add callback")
        self.connector.event_callbacks.append(callback)

    @property
    def status(self) -> ConnectionStatus:
        if self.connector:
            return self.connector.status
        raise ValueError(f"{self} is not bound to an account")


class ConnectionService(Service):
    supported_interface_types = {ConnectionInterface}

    def __init__(self, configs: List[ConfigUnion]) -> None:
        self.connections: Dict[int, ConnectorMixin] = {}
        self.event_callbacks: Dict[int, List[Callable[["MiraiEvent"], Awaitable[Any]]]] = {}
        conf_map: Dict[int, List[ConfigUnion]] = {}
        for conf in configs:
            conf_map.setdefault(conf.account, []).append(conf)
        for configs in conf_map.values():
            configs.sort(key=lambda x: isinstance(x, HttpClientConnector))
            # make sure the http client is the last one
            for conf in configs:
                self.update_from_config(conf)

    def update_from_config(self, config: ConfigUnion) -> None:
        account: int = config.account
        connector = CONFIG_MAP[config.__class__](config)
        if account not in self.connections:
            self.connections[account] = connector
        elif isinstance(connector, HttpClientConnector):
            connector.hook(self.connections[account])
        else:
            raise ValueError(
                f"{account} already has connector {self.connections[account]}, found {connector}"
            )

    async def mainline(self, mgr: LaunchManager) -> None:
        await asyncio.wait(
            [asyncio.create_task(connector.mainline(mgr)) for connector in self.connections.values()]
        )

    @property
    def launch_component(self) -> LaunchComponent:
        requirements: MutableSet[str] = set()
        for connector in self.connections.values():
            requirements.update(connector.dependency)
        return LaunchComponent("elizabeth.connection", requirements, self.mainline)

    def get_interface(self, interface_type: type):
        if interface_type is ConnectionInterface:
            return ConnectionInterface(self)
