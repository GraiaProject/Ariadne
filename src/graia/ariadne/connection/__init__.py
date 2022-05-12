import asyncio
from typing import Any, Dict, List, MutableSet

from graia.amnesia.launch.component import LaunchComponent
from graia.amnesia.launch.interface import ExportInterface
from graia.amnesia.launch.manager import LaunchManager
from graia.amnesia.launch.service import Service

from .config import ConfigUnion
from .connector import CONFIG_MAP, AbstractConnector, HttpClientConnector
from .util import CallMethod as CallMethod  # noqa: F401


class ConnectionInterface(ExportInterface):
    async def call(self, account: int, action: str, params: dict) -> Any:
        ...


class ConnectionService(Service):
    supported_interface_types = {ConnectionInterface}

    def __init__(self, configs: List[ConfigUnion]) -> None:
        self.connections: Dict[int, AbstractConnector] = {}
        conf_map: Dict[int, List[ConfigUnion]] = {}
        for conf in configs:
            conf_map.setdefault(conf.account, []).append(conf)
        for configs in conf_map.values():
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

    def get_interface(self, interface_type):
        return super().get_interface(interface_type)
