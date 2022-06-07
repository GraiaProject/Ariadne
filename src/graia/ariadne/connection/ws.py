import asyncio
import secrets
from typing import Any, Awaitable, Callable, Dict, List, MutableMapping, Optional
from weakref import WeakValueDictionary

from graia.amnesia.builtins.aiohttp import AiohttpClientInterface
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http.extra import HttpRequest
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
from launart import Launart
from launart.utilles import wait_fut
from loguru import logger
from yarl import URL

from graia.ariadne.connection import ConnectionMixin, ConnectionStatus
from graia.ariadne.connection.http import HttpClientConnection

from ..event import MiraiEvent
from ._info import WebsocketClientInfo, WebsocketServerInfo
from .util import CallMethod, build_event, get_router, validate_response

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
            self.status.session_key = data["session"]
            logger.success("Successfully got session key", style="green bold")
            return
        if sync_id in self.futures:
            self.futures[sync_id].set_result(data)
        elif "type" in data:
            self.status.alive = True
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
        self.status.session_key = None
        self.status.alive = False
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

    async def launch(self, mgr: Launart) -> None:
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
    http_interface: AiohttpClientInterface

    @property
    def stages(self):
        return {"blocking"}

    def __init__(self, config: WebsocketClientInfo) -> None:
        ConnectionMixin.__init__(self, config)
        self.futures = WeakValueDictionary()

    async def launch(self, mgr: Launart) -> None:
        self.http_interface = mgr.get_interface(AiohttpClientInterface)
        config = self.config
        async with self.stage("blocking"):
            rider = self.http_interface.websocket(
                str(
                    (URL(config.host) / "all").with_query(
                        {"qq": config.account, "verifyKey": config.verify_key}
                    )
                )
            )
            await wait_fut(
                [rider.use(self), self.wait_for("finished", "elizabeth.service")],
                return_when=asyncio.FIRST_COMPLETED,
            )

    @t.on(WebsocketConnectEvent)
    async def _(self, io: AbstractWebsocketIO) -> None:  # start authenticate
        self.ws_io = io
        self.status.alive = True
