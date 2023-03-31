import asyncio
import json as json_mod
import secrets
from typing import Any, Dict, MutableMapping, Optional
from weakref import WeakValueDictionary

from launart import Launart
from launart.utilles import wait_fut
from loguru import logger
from yarl import URL

from graia.amnesia.builtins.aiohttp import AiohttpClientInterface
from graia.amnesia.builtins.memcache import Memcache
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http.extra import HttpRequest
from graia.amnesia.transport.common.server import AbstractRouter
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

from . import ConnectionMixin
from ._info import T_Info, WebsocketClientInfo, WebsocketServerInfo
from .util import CallMethod, DatetimeJsonEncoder, build_event, validate_response

t = TransportRegistrar()


@t.apply
class WebsocketConnectionMixin(Transport, ConnectionMixin[T_Info]):
    ws_io: Optional[AbstractWebsocketIO]
    futures: MutableMapping[str, asyncio.Future]

    def __init__(self, info: T_Info) -> None:
        super().__init__(info=info)
        self.futures = WeakValueDictionary()

    @t.on(WebsocketReceivedEvent)
    @data_type(str)
    @json_require
    async def _(self, io: AbstractWebsocketIO, raw: Any) -> None:  # event pass and callback
        assert isinstance(raw, dict)
        if "code" in raw:  # something went wrong
            if raw["code"] in (2, 3, 4):
                await io.extra(WSConnectionClose)  # Invalidate session to allow reattempt
            validate_response(raw)  # raise it
        sync_id: str = raw.get("syncId", "#")
        data = raw.get("data", None)
        data = validate_response(data, raising=False)
        if isinstance(data, Exception):
            if sync_id in self.futures:
                self.futures[sync_id].set_exception(data)
            return
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
            logger.warning(f"Got unknown data: {raw}")

    @t.handle(WebsocketReconnect)
    async def _(self, _) -> bool:
        self._connection_fail()
        logger.warning("Websocket reconnecting in 5s...", style="dark_orange")
        await asyncio.sleep(5)
        logger.warning("Websocket reconnecting...", style="dark_orange")
        return True

    @t.on(WebsocketCloseEvent)
    async def _(self, _: AbstractWebsocketIO) -> None:
        from ..app import Ariadne

        app = Ariadne.current()
        await app.launch_manager.get_interface(Memcache).delete(f"account.{app.account}.version")

        self.status.session_key = None
        self.status.alive = False
        logger.info("Websocket connection closed", style="dark_orange")

    async def call(
        self,
        command: str,
        method: CallMethod,
        params: Optional[dict] = None,
        *,
        in_session: bool = True,
    ) -> Any:
        params = params or {}
        sync_id: str = secrets.token_urlsafe(12)
        fut = asyncio.get_running_loop().create_future()
        content: Dict[str, Any] = {
            "syncId": sync_id,
            "command": command,
            "content": params or {},
        }
        if method == CallMethod.RESTGET:
            content["subCommand"] = "get"
        elif method == CallMethod.RESTPOST:
            content["subCommand"] = "update"
        elif method == CallMethod.MULTIPART:
            return await super().call(command, method, params, in_session=in_session)
        self.futures[sync_id] = fut
        await self.status.wait_for_available()
        assert self.ws_io
        await self.ws_io.send(json_mod.dumps(content, cls=DatetimeJsonEncoder))
        return await fut


t = TransportRegistrar()


@t.apply
class WebsocketServerConnection(WebsocketConnectionMixin[WebsocketServerInfo]):
    """Websocket 服务器连接"""

    dependencies = {AbstractRouter}

    def __init__(self, info: WebsocketServerInfo) -> None:
        super().__init__(info)
        self.declares.append(WebsocketEndpoint(self.info.path))

    async def launch(self, mgr: Launart) -> None:
        router = mgr.get_interface(AbstractRouter)
        router.use(self)

    @t.on(WebsocketConnectEvent)
    async def _(self, io: AbstractWebsocketIO) -> None:
        req: HttpRequest = await io.extra(HttpRequest)
        for k, v in self.info.headers.items():
            if req.headers.get(k) != v:
                return await io.extra(WSConnectionClose)
        for k, v in self.info.params.items():
            if req.query_params.get(k) != v:
                return await io.extra(WSConnectionClose)
        await io.extra(WSConnectionAccept)
        await io.send(
            {
                "syncId": "#",
                "command": "verify",
                "content": {
                    "verifyKey": self.info.verify_key,
                    "sessionKey": None,
                    "qq": self.info.account,
                },
            }
        )
        self.ws_io = io


t = TransportRegistrar()


@t.apply
class WebsocketClientConnection(WebsocketConnectionMixin[WebsocketClientInfo]):
    """Websocket 客户端连接"""

    dependencies = {AiohttpClientInterface}
    http_interface: AiohttpClientInterface

    @property
    def stages(self):
        return {"blocking"}

    async def launch(self, mgr: Launart) -> None:
        self.http_interface = mgr.get_interface(AiohttpClientInterface)
        config = self.info
        async with self.stage("blocking"):
            rider = self.http_interface.websocket(
                str(
                    (URL(config.host) / "all").with_query(
                        {"qq": config.account, "verifyKey": config.verify_key}
                    )
                ),
                heartbeat=30.0,
            )
            await wait_fut(
                [rider.use(self), mgr.status.wait_for_sigexit()],
                return_when=asyncio.FIRST_COMPLETED,
            )

    @t.on(WebsocketConnectEvent)
    async def _(self, io: AbstractWebsocketIO) -> None:  # start authenticate
        self.ws_io = io
        self.status.alive = True
