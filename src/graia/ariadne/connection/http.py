import asyncio
from typing import Any, Optional

from aiohttp import FormData
from graia.amnesia.builtins.aiohttp import AiohttpClientInterface
from graia.amnesia.json import Json
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http import AbstractServerRequestIO, HttpEndpoint
from graia.amnesia.transport.common.http.extra import HttpRequest
from launart import Launart
from launart.utilles import wait_fut
from loguru import logger

from graia.ariadne.connection import ConnectionMixin

from ..exception import InvalidSession
from ._info import HttpClientInfo, HttpServerInfo
from .util import CallMethod, build_event, get_router, validate_response


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
        self.status.connected = True
        self.status.alive = True
        event = build_event(data)
        await asyncio.gather(*(callback(event) for callback in self.event_callbacks))
        return {"command": "", "data": {}}

    async def launch(self, mgr: Launart) -> None:
        router = get_router(mgr)
        router.use(self)


class HttpClientConnection(ConnectionMixin[HttpClientInfo]):
    dependencies = {"http.universal_client"}
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
        self.status.session_key = session_key

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
            self.status.session_key = None
            raise

    @property
    def stages(self):
        return {} if self.is_hook else {"blocking"}

    async def launch(self, mgr: Launart) -> None:
        self.http_interface = mgr.get_interface(AiohttpClientInterface)
        if self.is_hook:
            return
        async with self.stage("blocking"):
            while not mgr.launchables["elizabeth.service"].status.finished:
                try:
                    if not self.status.session_key:
                        logger.info("HttpClient: authenticate", style="dark_orange")
                        await self.http_auth()
                    data = await self.request(
                        "GET",
                        self.config.get_url("fetchMessage"),
                        {"sessionKey": self.status.session_key, "count": 10},
                    )
                    self.status.alive = True
                except Exception as e:
                    self.status.session_key = None
                    self.status.alive = False
                    logger.exception(e)
                    continue
                assert isinstance(data, list)
                for event_data in data:
                    event = build_event(event_data)
                    await asyncio.gather(*(callback(event) for callback in self.event_callbacks))
                await wait_fut(
                    [asyncio.sleep(0.5), self.wait_for("finished", "elizabeth.service")],
                    return_when=asyncio.FIRST_COMPLETED,
                )
