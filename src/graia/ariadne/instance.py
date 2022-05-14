from typing import Optional

from graia.amnesia.launch.interface import ExportInterface
from graia.amnesia.launch.service import Service
from graia.broadcast import Broadcast

from graia.ariadne.model import AriadneStatus

from .connection.connector import ConnectorMixin


class Ariadne(ExportInterface["ElizabethService"]):
    broadcast: Optional[Broadcast]
    account: Optional[int]
    connector: Optional[ConnectorMixin]
    status: AriadneStatus

    def __init__(self, service: "ElizabethService") -> None:
        self.service = service


class ElizabethService(Service):
    broadcast: Optional[Broadcast]

    def __init__(self) -> None:
        super().__init__()
