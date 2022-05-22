import abc
import asyncio
import secrets
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Literal,
    MutableMapping,
    Optional,
    Set,
    Type,
    Union,
)
from weakref import WeakValueDictionary

from aiohttp import FormData
from graia.amnesia.builtins.aiohttp import AiohttpClientInterface
from graia.amnesia.json import Json
from graia.amnesia.launch.interface import ExportInterface
from graia.amnesia.launch.manager import LaunchManager
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http import AbstractServerRequestIO, HttpEndpoint
from graia.amnesia.transport.common.http.extra import HttpRequest
from graia.amnesia.transport.common.status import (
    ConnectionStatus as BaseConnectionStatus,
)
from graia.amnesia.transport.common.websocket import (
    AbstractWebsocketIO,
    WebsocketCloseEvent,
    WebsocketConnectEvent,
    WebsocketEndpoint,
    WebsocketReceivedEvent,
    WebsocketReconnect,
    WSConnectionAccept,
    WSConnectionClose,
)
from graia.amnesia.transport.common.websocket.shortcut import data_type, json_require
from graia.amnesia.transport.utilles import TransportRegistrar
from loguru import logger
from typing_extensions import Self
from yarl import URL

from ..event import MiraiEvent
from ..exception import InvalidSession
from ..typing import Sentinel
from ._info import (
    HttpClientInfo,
    HttpServerInfo,
    T_Info,
    U_Info,
    WebsocketClientInfo,
    WebsocketServerInfo,
)
from .util import CallMethod, build_event, get_router, validate_response

if TYPE_CHECKING:
    from ..service import ElizabethService


class ConnectionStatus(BaseConnectionStatus):
    def __init__(self) -> None:
        self.session_key: Optional[str] = None
        self.alive: bool = False
        self.connected: bool = False
        super().__init__("elizabeth.connection")

    def update(
        self,
        session_key: Union[str, None, Literal[Sentinel]] = Sentinel,
        connected: Optional[bool] = None,
        alive: Optional[bool] = None,
    ):
        past = self.frame
        if session_key is not Sentinel:
            self.session_key = session_key
            self.connected = session_key is not None
        if connected is not None:
            self.connected = connected
        if alive is not None:
            self.alive = alive
        self.notify(past)

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
                ]
            )
        )


class ConnectionMixin(Generic[T_Info]):
    status: ConnectionStatus
    config: T_Info
    dependencies: Set[str]

    fallback: Optional["HttpClientConnection"]
    http_interface: AiohttpClientInterface
    event_callbacks: List[Callable[[MiraiEvent], Awaitable[Any]]]

    def __init__(self, config: T_Info) -> None:
        self.config = config
        self.fallback = None
        self.event_callbacks = []
        self.status = ConnectionStatus()

    @abc.abstractmethod
    async def mainline(self, mgr: LaunchManager) -> None:
        ...

    async def call(self, command: str, method: CallMethod, params: Optional[dict] = None) -> Any:
        if self.fallback:
            return await self.fallback.call(command, method, params)
        raise NotImplementedError(
            f"Connection {self} can't perform {command!r}, consider configuring a HttpClientConnection?"
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.status} with {len(self.event_callbacks)} callbacks>"


t = TransportRegistrar()


@t.apply
class WebsocketConnectionMixin(Transport):
    ws_io: Optional[AbstractWebsocketIO]
    futures: MutableMapping[str, asyncio.Future]
    status: ConnectionStatus
    fallback: Optional["HttpClientConnection"]
    event_callbacks: List[Callable[[MiraiEvent], Awaitable[Any]]]

    @t.on(WebsocketReceivedEvent)
    @data_type(str)
    @json_require
    async def _(self, _: AbstractWebsocketIO, raw: Any) -> None:  # event pass and callback
        assert isinstance(raw, dict)
        if "code" in raw:  # something went wrong
            validate_response(raw)  # raise it
        sync_id: str = raw.get("syncId", "#")
        data = raw.get("data", None)
        data = validate_response(data)
        if "session" in data:
            self.status.update(session_key=data["session"])
            logger.success("Successfully got session key", style="green bold")
            return
        if sync_id in self.futures:
            self.futures[sync_id].set_result(data)
        elif "type" in data:
            self.status.update(alive=True)
            event = build_event(data)
            await asyncio.gather(*(callback(event) for callback in self.event_callbacks))
        else:
            logger.warning(f"Got unknown data: {data}")

    @t.handle(WebsocketReconnect)
    async def _(self, _) -> bool:
        logger.warning("Websocket reconnecting in 5s...", style="dark_orange")
        await asyncio.sleep(5)
        logger.warning("Websocket reconnecting...", style="dark_orange")
        return True

    @t.on(WebsocketCloseEvent)
    async def _(self, _: AbstractWebsocketIO) -> None:
        self.status.update(session_key=None, alive=False)
        logger.info("Websocket connection closed", style="dark_orange")

    async def call(self, command: str, method: CallMethod, params: Optional[dict] = None) -> Any:
        params = params or {}
        sync_id: str = secrets.token_urlsafe(12)
        fut = asyncio.get_running_loop().create_future()
        content: Dict[str, Any] = {"syncId": sync_id, "command": command, "content": params or {}}
        if method == CallMethod.RESTGET:
            content["subCommand"] = "get"
        elif method == CallMethod.RESTPOST:
            content["subCommand"] = "update"
        elif method == CallMethod.MULTIPART:
            if self.fallback:
                return await self.fallback.call(command, method, params)
            raise NotImplementedError(
                f"Connection {self} can't perform {command!r}, consider configuring a HttpClientConnection?"
            )
        self.futures[sync_id] = fut
        await self.status.wait_for_available()
        assert self.ws_io
        await self.ws_io.send(content)
        return await fut


t = TransportRegistrar()


@t.apply
class WebsocketServerConnection(WebsocketConnectionMixin, ConnectionMixin[WebsocketServerInfo]):
    dependencies = {"http.universal_server"}

    def __init__(self, config: WebsocketServerInfo) -> None:
        ConnectionMixin.__init__(self, config)
        self.declares.append(WebsocketEndpoint(self.config.path))
        self.futures = WeakValueDictionary()

    async def mainline(self, mgr: LaunchManager) -> None:
        router = get_router(mgr)
        router.use(self)

    @t.on(WebsocketConnectEvent)
    async def _(self, io: AbstractWebsocketIO) -> None:
        req: HttpRequest = await io.extra(HttpRequest)
        for k, v in self.config.headers:
            if req.headers.get(k) != v:
                return await io.extra(WSConnectionClose)
        for k, v in self.config.params:
            if req.query_params.get(k) != v:
                return await io.extra(WSConnectionClose)
        await io.extra(WSConnectionAccept)
        logger.info("WebsocketServer")
        await io.send(
            {
                "syncId": "#",
                "command": "verify",
                "content": {
                    "verifyKey": self.config.verify_key,
                    "sessionKey": None,
                    "qq": self.config.account,
                },
            }
        )
        self.ws_io = io


t = TransportRegistrar()


@t.apply
class WebsocketClientConnection(WebsocketConnectionMixin, ConnectionMixin[WebsocketClientInfo]):
    dependencies = {"http.universal_client"}

    def __init__(self, config: WebsocketClientInfo) -> None:
        ConnectionMixin.__init__(self, config)
        self.futures = WeakValueDictionary()

    async def mainline(self, _) -> None:
        config = self.config
        await self.http_interface.websocket(
            str((URL(config.host) / "all").with_query({"qq": config.account, "verifyKey": config.verify_key}))
        ).use(self)

    @t.on(WebsocketConnectEvent)
    async def _(self, io: AbstractWebsocketIO) -> None:  # start authenticate
        self.ws_io = io
        self.status.update(alive=True)


class HttpServerConnection(ConnectionMixin[HttpServerInfo], Transport):
    dependencies = {"http.universal_server"}

    def __init__(self, config: HttpServerInfo) -> None:
        super().__init__(config)
        self.handlers[HttpEndpoint(self.config.path, ["POST"])] = self.__class__.handle_request

    async def handle_request(self, io: AbstractServerRequestIO):
        req: HttpRequest = await io.extra(HttpRequest)
        if req.headers.get("qq") != str(self.config.account):
            return
        for k, v in self.config.headers:
            if req.headers.get(k) != v:
                return "Authorization failed", {"status": 401}
        data = Json.deserialize((await io.read()).decode("utf-8"))
        assert isinstance(data, dict)
        self.status.update(connected=True, alive=True)
        event = build_event(data)
        await asyncio.gather(*(callback(event) for callback in self.event_callbacks))
        return {"command": "", "data": {}}

    async def mainline(self, mgr: LaunchManager) -> None:
        router = get_router(mgr)
        router.use(self)


class HttpClientConnection(ConnectionMixin[HttpClientInfo]):
    dependencies = {"http.universal_client"}

    def __init__(self, config: HttpClientInfo) -> None:
        super().__init__(config)

    async def request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        data: Optional[Any] = None,
        json: Optional[dict] = None,
    ) -> Any:
        if data and isinstance(data, dict):
            form = FormData(quote_fields=False)
            for k, v in data.values():
                form.add_field(k, **v)
            data = form
        rider = await self.http_interface.request(method, url, params=params, data=data, json=json)
        byte_data = await rider.io().read()
        result = Json.deserialize(byte_data.decode("utf-8"))
        return validate_response(result)

    async def http_auth(self) -> None:
        data = await self.request(
            "POST",
            self.config.get_url("verify"),
            json={"verifyKey": self.config.verify_key},
        )
        session_key = data["session"]
        await self.request(
            "POST",
            self.config.get_url("bind"),
            json={"qq": self.config.account, "sessionKey": session_key},
        )
        self.status.update(session_key=session_key)

    async def call(self, command: str, method: CallMethod, params: Optional[dict] = None) -> Any:
        params = params or {}
        command = command.replace("_", "/")
        while not self.status.connected:
            await self.status.wait_for_update()
        if not self.status.session_key:
            await self.http_auth()
        try:
            if method in (CallMethod.GET, CallMethod.RESTGET):
                return await self.request("GET", self.config.get_url(command), params=params)
            elif method in (CallMethod.POST, CallMethod.RESTPOST):
                return await self.request("POST", self.config.get_url(command), json=params)
            elif method == CallMethod.MULTIPART:
                return await self.request("POST", self.config.get_url(command), data=params)
        except InvalidSession:
            self.status.update(session_key=None)
            raise

    async def mainline(self, _) -> None:
        while True:
            try:
                if not self.status.session_key:
                    logger.info("HttpClient: authenticate", style="dark_orange")
                    await self.http_auth()
                data = await self.request(
                    "GET",
                    self.config.get_url("fetchMessage"),
                    {"sessionKey": self.status.session_key, "count": 10},
                )
            except Exception as e:
                self.status.update(session_key=None, alive=False)
                logger.exception(e)
                continue
            self.status.update(alive=True)
            assert isinstance(data, list)
            for event_data in data:
                event = build_event(event_data)
                await asyncio.gather(*(callback(event) for callback in self.event_callbacks))
            await asyncio.sleep(0.5)


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
        self, command: str, method: CallMethod, params: dict, *, account: Optional[int] = None, in_session: bool = True
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
