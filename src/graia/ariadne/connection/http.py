import asyncio
import json as json_mod
from typing import Any, Optional

from aiohttp import FormData
from launart import Launart
from launart.utilles import wait_fut
from loguru import logger

from graia.amnesia.builtins.aiohttp import AiohttpClientInterface
from graia.amnesia.builtins.memcache import Memcache
from graia.amnesia.json import Json
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http import AbstractServerRequestIO, HttpEndpoint
from graia.amnesia.transport.common.http.extra import HttpRequest
from graia.amnesia.transport.common.server import AbstractRouter

from ..exception import InvalidSession
from . import ConnectionMixin
from ._info import HttpClientInfo, HttpServerInfo
from .util import CallMethod, DatetimeJsonEncoder, build_event, validate_response


class HttpServerConnection(ConnectionMixin[HttpServerInfo], Transport):
    """HTTP 服务器连接"""

    dependencies = {AbstractRouter}

    def __init__(self, config: HttpServerInfo) -> None:
        super().__init__(config)
        self.handlers[HttpEndpoint(self.info.path, ["POST"])] = self.__class__.handle_request

    async def handle_request(self, io: AbstractServerRequestIO):
        req: HttpRequest = await io.extra(HttpRequest)
        if req.headers.get("qq") != str(self.info.account):
            return "Not registered account", {"status": 403}
        for k, v in self.info.headers.items():
            if req.headers.get(k) != v:
                return "Authorization failed", {"status": 401}
        data = Json.deserialize((await io.read()).decode("utf-8"))
        assert isinstance(data, dict)
        self.status.connected = True
        self.status.alive = True
        event = build_event(data)
        await asyncio.gather(*(callback(event) for callback in self.event_callbacks))
        return {"command": "", "data": {}}

    async def launch(self, mgr: Launart) -> None:
        router = mgr.get_interface(AbstractRouter)
        router.use(self)


class HttpClientConnection(ConnectionMixin[HttpClientInfo]):
    """HTTP 客户端连接"""

    dependencies = {AiohttpClientInterface}
    http_interface: AiohttpClientInterface

    def __init__(self, config: HttpClientInfo) -> None:
        super().__init__(config)
        self.is_hook: bool = False

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
            for k, v in data.items():
                form.add_field(k, **v) if isinstance(v, dict) else form.add_field(k, v)
            data = form
        if json:
            data = json_mod.dumps(json, cls=DatetimeJsonEncoder)
        rider = await self.http_interface.request(method, url, params=params, data=data)
        byte_data = await rider.io().read()
        result = Json.deserialize(byte_data.decode("utf-8"))
        return validate_response(result)

    async def http_auth(self) -> None:
        from ..app import Ariadne

        app = Ariadne.current()
        await app.launch_manager.get_interface(Memcache).delete(f"account.{app.account}.version")

        data = await self.request(
            "POST",
            self.info.get_url("verify"),
            json={"verifyKey": self.info.verify_key},
        )
        session_key = data["session"]
        await self.request(
            "POST",
            self.info.get_url("bind"),
            json={"qq": self.info.account, "sessionKey": session_key},
        )
        self.status.session_key = session_key

    async def call(
        self, command: str, method: CallMethod, params: Optional[dict] = None, *, in_session: bool = True
    ) -> Any:
        params = params or {}
        command = command.replace("_", "/")
        while not self.status.connected:
            await self.status.wait_for_update()
        if in_session:
            if not self.status.session_key:
                await self.http_auth()
            params["sessionKey"] = self.status.session_key
        try:
            if method in (CallMethod.GET, CallMethod.RESTGET):
                return await self.request("GET", self.info.get_url(command), params=params)
            elif method in (CallMethod.POST, CallMethod.RESTPOST):
                return await self.request("POST", self.info.get_url(command), json=params)
            elif method == CallMethod.MULTIPART:
                return await self.request("POST", self.info.get_url(command), data=params)
        except InvalidSession:
            self.status.session_key = None
            raise

    @property
    def stages(self):
        return {} if self.is_hook else {"blocking"}

    async def launch(self, mgr: Launart) -> None:
        self.http_interface = mgr.get_interface(AiohttpClientInterface)
        exit_signal = asyncio.create_task(mgr.status.wait_for_sigexit())
        if self.is_hook:  # FIXME
            await exit_signal
            return
        async with self.stage("blocking"):
            while not exit_signal.done():
                try:
                    if not self.status.session_key:
                        logger.info("HttpClient: authenticate", style="dark_orange")
                        await self.http_auth()
                    data = await self.request(
                        "GET",
                        self.info.get_url("fetchMessage"),
                        {"sessionKey": self.status.session_key, "count": 10},
                    )
                    self.status.alive = True
                except Exception as e:
                    self.status.session_key = None
                    self.status.alive = False
                    self._connection_fail()
                    logger.exception(e)
                    continue
                assert isinstance(data, list)
                for event_data in data:
                    event = build_event(event_data)
                    await asyncio.gather(*(callback(event) for callback in self.event_callbacks))
                await wait_fut(
                    [asyncio.sleep(0.5), exit_signal],
                    return_when=asyncio.FIRST_COMPLETED,
                )
