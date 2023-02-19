from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, ClassVar, Generic
from typing_extensions import Self

from launart import ExportInterface, Launchable, LaunchableStatus
from statv import Stats

from graia.amnesia.transport.common.status import ConnectionStatus as BaseConnectionStatus

from ..event import MiraiEvent
from ..util import camel_to_snake
from ._info import HttpClientInfo, HttpServerInfo, T_Info, U_Info, WebsocketClientInfo, WebsocketServerInfo
from .util import CallMethod

if TYPE_CHECKING:
    from ..service import ElizabethService


class ConnectionStatus(BaseConnectionStatus, LaunchableStatus):
    """连接状态"""

    alive = Stats[bool]("alive", default=False)

    def __init__(self) -> None:
        self._session_key: str | None = None
        super().__init__()

    @property
    def session_key(self) -> str | None:
        return self._session_key

    @session_key.setter
    def session_key(self, value: str | None) -> None:
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
    info: T_Info
    dependencies: ClassVar[set[str | type[ExportInterface]]]

    fallback: HttpClientConnection | None
    event_callbacks: list[Callable[[MiraiEvent], Awaitable[Any]]]
    _connection_fail: Callable

    @property
    def required(self) -> set[str | type[ExportInterface]]:
        return self.dependencies

    @property
    def stages(self):
        return {}

    def __init__(self, info: T_Info) -> None:
        self.id = ".".join(
            [
                "elizabeth",
                "connection",
                str(info.account),
                camel_to_snake(self.__class__.__qualname__),
            ]
        )
        self.info = info
        self.fallback = None
        self.event_callbacks = []
        self.status = ConnectionStatus()

    async def call(
        self,
        command: str,
        method: CallMethod,
        params: dict | None = None,
        *,
        in_session: bool = True,
    ) -> Any:
        """调用下层 API

        Args:
            command (str): 命令
            method (CallMethod): 调用类型
            params (dict, optional): 调用参数
        """
        if self.fallback:
            return await self.fallback.call(command, method, params, in_session=in_session)
        raise NotImplementedError(
            f"Connection {self} can't perform {command!r}, consider configuring a HttpClientConnection?"
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.status} with {len(self.event_callbacks)} callbacks>"


from .http import HttpClientConnection as HttpClientConnection  # noqa: E402
from .http import HttpServerConnection as HttpServerConnection  # noqa: E402
from .ws import WebsocketClientConnection as WebsocketClientConnection  # noqa: E402
from .ws import WebsocketServerConnection as WebsocketServerConnection  # noqa: E402

CONFIG_MAP: dict[type[U_Info], type[ConnectionMixin]] = {
    HttpClientInfo: HttpClientConnection,
    HttpServerInfo: HttpServerConnection,
    WebsocketClientInfo: WebsocketClientConnection,
    WebsocketServerInfo: WebsocketServerConnection,
}


class ConnectionInterface(ExportInterface["ElizabethService"]):
    """Elizabeth 连接接口"""

    service: ElizabethService
    connection: ConnectionMixin | None

    def __init__(self, service: ElizabethService, account: int | None = None) -> None:
        """初始化连接接口

        Args:
            service (ElizabethService): 连接服务
            account (int, optional): 对应账号
        """
        self.service = service
        self.connection = None
        if account:
            if account not in service.connections:
                raise ValueError(f"Account {account} not found")
            self.connection = service.connections[account]

    def bind(self, account: int) -> Self:
        """绑定账号, 返回一个新实例

        Args:
            account (int): 账号

        Returns:
            ConnectionInterface: 新实例
        """
        return ConnectionInterface(self.service, account)

    async def call(
        self,
        command: str,
        method: CallMethod,
        params: dict,
        *,
        account: int | None = None,
        in_session: bool = True,
    ) -> Any:
        """发起一个调用

        Args:
            command (str): 调用命令
            method (CallMethod): 调用方法
            params (dict): 调用参数
            account (Optional[int], optional): 账号. Defaults to None.
            in_session (bool, optional): 是否在会话中. Defaults to True.

        Returns:
            Any: 调用结果
        """
        if account is None:
            connection = self.connection
        else:
            connection = self.service.connections.get(account)
        if connection is None:
            raise ValueError(f"Unable to find connection to execute {command}")

        return await connection.call(command, method, params, in_session=in_session)

    def add_callback(self, callback: Callable[[MiraiEvent], Awaitable[Any]]) -> None:
        """添加事件回调

        Args:
            callback (Callable[[MiraiEvent], Awaitable[Any]]): 回调函数
        """
        if self.connection is None:
            raise ValueError("Unable to find connection to add callback")
        self.connection.event_callbacks.append(callback)

    @property
    def status(self) -> ConnectionStatus:
        """获取连接状态"""
        if self.connection:
            return self.connection.status
        raise ValueError(f"{self} is not bound to an account")
