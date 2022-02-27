"""反向 Adapter, 作为服务器让 mirai-api-http 连接"""

import asyncio
import json
from typing import Any, Dict, Optional, Type

from aiohttp import ClientSession
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from graia.broadcast import Broadcast
from uvicorn import Config, Server

from ..model import CallMethod, DatetimeEncoder, MiraiSession
from ..util import yield_with_timeout
from . import Adapter
from .util import SyncIDManager, validate_response


class NoSigServer(Server):
    """不注册 Signal 的服务器"""

    def install_signal_handlers(self) -> None:
        return


class ReverseAdapter(Adapter):
    """反向 Adapter 基类"""

    server: NoSigServer
    asgi: FastAPI
    mirai_session: MiraiSession
    broadcast: Broadcast
    session: Optional[ClientSession]

    def __init__(
        self,
        broadcast: Broadcast,
        mirai_session: MiraiSession,
        route: str = "/",
        log: bool = False,
        *,
        app: Optional[FastAPI] = None,
        port: int = 8000,
        server_cls: Type[NoSigServer] = NoSigServer,
        **config_kwargs: Any,
    ):
        super().__init__(broadcast, mirai_session)
        self.asgi = app or FastAPI()
        self.route = route
        LOG_CONFIG = {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "default": {
                    "class": "graia.ariadne.util.LoguruHandler",
                },
            },
            "loggers": {
                "uvicorn.error": {"handlers": ["default"] if log else [], "level": "INFO"},
                "uvicorn.access": {
                    "handlers": ["default"] if log else [],
                    "level": "INFO",
                },
            },
            "formatters": {
                "default": {"use_colors": True},
                "access": {"use_colors": True},
            },
        }
        self.server = server_cls(Config(self.asgi, port=port, log_config=LOG_CONFIG, **config_kwargs))

    async def stop(self) -> None:
        """停止服务器"""
        self.server.should_exit = True
        await super().stop()

    async def fetch_cycle(self):
        self.session = ClientSession()
        await self.server.serve()
        await self.session.close()


class WebhookAdapter(ReverseAdapter):
    """Webhook (反向 HTTP) Adapter"""

    def __init__(
        self,
        broadcast: Broadcast,
        mirai_session: MiraiSession,
        route: str = "/",
        extra_headers: Optional[Dict[str, str]] = None,
        log: bool = False,
        *,
        app: Optional[FastAPI] = None,
        port: int = 8000,
        server_cls: Type[NoSigServer] = NoSigServer,
        **config_kwargs: Any,
    ):
        super().__init__(
            broadcast,
            mirai_session,
            route,
            log,
            app=app,
            port=port,
            server_cls=server_cls,
            **config_kwargs,
        )
        self.asgi.add_api_route(self.route, self.http_endpoint, methods=["POST"])
        self.extra_headers: Dict[str, str] = extra_headers or {}

    async def http_endpoint(self, request: Request):
        header: Dict[str, str] = dict(request.headers.items())
        if header["qq"] == str(self.mirai_session.account):
            for key, val in self.extra_headers.items():
                key = key.lower()
                if val != header.get(key, ""):
                    raise HTTPException(status_code=401, detail="Authorization Failed")
            await self.event_queue.put(self.build_event(await request.json()))
        return {"command": "", "data": {}}


class ReverseWebsocketAdapter(ReverseAdapter):
    """反向 WebSocket Adapter"""

    def __init__(
        self,
        broadcast: Broadcast,
        mirai_session: MiraiSession,
        route: str = "/",
        extra_headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
        log: bool = False,
        *,
        app: Optional[FastAPI] = None,
        port: int = 8000,
        server_cls: Type[NoSigServer] = NoSigServer,
        **config_kwargs: Any,
    ):
        super().__init__(
            broadcast,
            mirai_session,
            route,
            log,
            app=app,
            port=port,
            server_cls=server_cls,
            **config_kwargs,
        )
        self.asgi.add_api_websocket_route(self.route, self.websocket_endpoint)
        self.id_manager = SyncIDManager()
        self.websocket: Optional[WebSocket] = None
        self.extra_headers: Dict[str, str] = extra_headers or {}
        self.query_params: Dict[str, str] = query_params or {}

    async def websocket_endpoint(self, websocket: WebSocket):
        header: Dict[str, str] = dict(websocket.headers.items())
        query_params: Dict[str, str] = dict(websocket.query_params.items())
        for key, val in self.extra_headers.items():
            key = key.lower()
            if val != header.get(key, ""):
                raise HTTPException(status_code=401, detail="Authorization Failed")
        for key, val in self.query_params.items():
            if val != query_params.get(key, ""):
                raise HTTPException(status_code=401, detail="Authorization Failed")
        await websocket.accept()
        self.websocket = websocket
        try:
            asyncio.create_task(self.get_session_key())
            while True:
                raw_data = await websocket.receive_json()
                sync_id: int = int(raw_data["syncId"] or -1)
                data: dict = raw_data["data"]
                if not self.id_manager.free(sync_id, validate_response(data)):
                    await self.event_queue.put(self.build_event(data))
        except WebSocketDisconnect:
            self.websocket = None
            self.mirai_session.session_key = None

    async def get_session_key(self):
        if not self.mirai_session.single_mode:
            data = await self.call_api(
                "verify",
                CallMethod.POST,
                {
                    "verifyKey": self.mirai_session.verify_key,
                    "qq": self.mirai_session.account,
                    "sessionKey": None,
                },
                meta=True,
            )
            self.mirai_session.session_key = data["session"]

    async def call_cycle(self):
        async for call in yield_with_timeout(self.call_queue.get, lambda: self.running):
            if (
                not any([self.mirai_session.session_key, self.mirai_session.single_mode, call.meta])
                or not self.websocket
            ):
                await self.call_queue.put(call)
                continue
            sync_id: int = self.id_manager.allocate(call.future)
            content = {
                "syncId": str(sync_id),
                "command": call.action.replace("/", "_"),
                "content": call.data,
            }
            if call.method == CallMethod.RESTGET:
                content["subCommand"] = "get"
            elif call.method == CallMethod.RESTPOST:
                content["subCommand"] = "update"
            elif call.method == CallMethod.MULTIPART:
                self.id_manager.free(
                    sync_id,
                    NotImplementedError(f"Unsupported operation for ReverseWebsocketAdapter: {call.method}"),
                )
            await self.websocket.send_text(json.dumps(content, cls=DatetimeEncoder))
