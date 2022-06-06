from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Type,
)

from graia.amnesia.transport.common.status import (
    ConnectionStatus as BaseConnectionStatus,
)
from launart import ExportInterface, Launchable, LaunchableStatus
from statv import Stats
from typing_extensions import Self

from ..event import MiraiEvent
from ..util import camel_to_snake
from ._info import (
    HttpClientInfo,
    HttpServerInfo,
    T_Info,
    U_Info,
    WebsocketClientInfo,
    WebsocketServerInfo,
)
from .util import CallMethod

if TYPE_CHECKING:
    from ..service import ElizabethService


class ConnectionStatus(BaseConnectionStatus, LaunchableStatus):
    alive = Stats[bool]("alive", default=False)

    def __init__(self) -> None:
        self._session_key: Optional[str] = None
        super().__init__()

    @property
    def session_key(self) -> Optional[str]:
        return self._session_key

    @session_key.setter
    def session_key(self, value: Optional[str]) -> None:
        self._session_key = value
        self.connected = value is not None

    @property
    def available(self) -> bool:
        return bool(self.connected and self.session_key and self.alive)

    def __repr__(self) -> str:
        return "<ConnectionStatus {}>".format(
            " ".join(
                [
                    f"connected={self.connected}",
                    f"alive={self.alive}",
                    f"verified={self.session_key is not None}",
                    f"stage={self.stage}",
                ]
            )
        )


class ConnectionMixin(Launchable, Generic[T_Info]):
    status: ConnectionStatus
    config: T_Info
    dependencies: Set[str]

    fallback: Optional["HttpClientConnection"]
    event_callbacks: List[Callable[[MiraiEvent], Awaitable[Any]]]

    @property
    def required(self) -> Set[str]:
        return self.dependencies

    @property
    def stages(self):
        return {}

    def __init__(self, config: T_Info) -> None:
        self.id = ".".join(
            [
                "elizabeth",
                "connection",
                str(config.account),
                camel_to_snake(self.__class__.__qualname__),
            ]
        )
        self.config = config
        self.fallback = None
        self.event_callbacks = []
        self.status = ConnectionStatus()

    async def call(self, command: str, method: CallMethod, params: Optional[dict] = None) -> Any:
        if self.fallback:
            return await self.fallback.call(command, method, params)
        raise NotImplementedError(
            f"Connection {self} can't perform {command!r}, consider configuring a HttpClientConnection?"
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.status} with {len(self.event_callbacks)} callbacks>"


from .http import HttpClientConnection, HttpServerConnection  # noqa: E402
from .ws import WebsocketClientConnection, WebsocketServerConnection  # noqa: E402

CONFIG_MAP: Dict[Type[U_Info], Type[ConnectionMixin]] = {
    HttpClientInfo: HttpClientConnection,
    HttpServerInfo: HttpServerConnection,
    WebsocketClientInfo: WebsocketClientConnection,
    WebsocketServerInfo: WebsocketServerConnection,
}


class ConnectionInterface(ExportInterface["ElizabethService"]):
    service: "ElizabethService"
    connection: Optional[ConnectionMixin]

    def __init__(self, service: "ElizabethService", account: Optional[int] = None) -> None:
        self.service = service
        self.connection = None
        if account:
            if account not in service.connections:
                raise ValueError(f"Account {account} not found")
            self.connection = service.connections[account]

    def bind(self, account: int) -> Self:
        return ConnectionInterface(self.service, account)

    async def _call(
        self, command: str, method: CallMethod, params: dict, *, account: Optional[int] = None
    ) -> Any:
        connection = self.connection
        if account is not None:
            connection = self.service.connections.get(account)
        if connection is None:
            raise ValueError(f"Unable to find connection to execute {command}")
        return await connection.call(command, method, params)

    async def call(
        self,
        command: str,
        method: CallMethod,
        params: dict,
        *,
        account: Optional[int] = None,
        in_session: bool = True,
    ) -> Any:
        if in_session:
            await self.status.wait_for_available()  # wait until session_key is present
            session_key = self.status.session_key
            params["sessionKey"] = session_key
        return await self._call(command, method, params, account=account)

    def add_callback(self, callback: Callable[[MiraiEvent], Awaitable[Any]]) -> None:
        if self.connection is None:
            raise ValueError("Unable to find connection to add callback")
        self.connection.event_callbacks.append(callback)

    @property
    def status(self) -> ConnectionStatus:
        if self.connection:
            return self.connection.status
        raise ValueError(f"{self} is not bound to an account")
