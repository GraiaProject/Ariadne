"""反向 Adapter, 作为服务器让 mirai-api-http 连接"""

import asyncio
import json
from typing import Any, Dict, FrozenSet, Optional, Type, Union

from aiohttp import ClientSession, FormData
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from graia.broadcast import Broadcast
from loguru import logger
from uvicorn import Config, Server

from graia.ariadne.adapter.forward import HttpAdapter

from ..model import CallMethod, DatetimeEncoder, MiraiSession
from ..util import await_predicate
from . import Adapter
from .util import validate_response


class NoSigServer(Server):
    """不注册 Signal 的服务器"""

    def install_signal_handlers(self) -> None:
        return


class ReverseAdapter(Adapter):
    """反向 Adapter 基类"""

    tags: FrozenSet[str] = frozenset(["reverse"])

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
        log: bool = True,
        *,
        app: Optional[FastAPI] = None,
        port: int = 8000,
        server_cls: Type[NoSigServer] = NoSigServer,
        **config_kwargs: Any,
    ):
        """初始化 ReverseAdapter

        Args:
            broadcast (Broadcast): 事件系统
            mirai_session (MiraiSession): MiraiSession 实例
            route (str, optional): 服务路径. Defaults to "/".
            log (bool, optional): 是否启用连接日志. Defaults to True.
            app (Optional[FastAPI], optional): ASGI 应用. Defaults to None.
            port (int, optional): 服务端口. Defaults to 8000.
            server_cls (Type[NoSigServer], optional): Server 类. Defaults to NoSigServer.
            **config_kwargs (Any, optional): 额外配置参数. Defaults to {}.
        """
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
                "uvicorn.access": {"handlers": ["default"] if log else [], "level": "INFO"},
            },
        }
        self.server = server_cls(Config(self.asgi, port=port, log_config=LOG_CONFIG, **config_kwargs))

    async def stop(self) -> None:
        """停止服务器"""
        self.running = False
        self.server.should_exit = True
        try:
            await asyncio.wait_for(self.fetch_task, timeout=5.0)
        except asyncio.TimeoutError:
            self.server.force_exit = True
        await self.fetch_task
        self.fetch_task = None

    async def fetch_cycle(self):
        async with ClientSession() as session:
            self.session = session
            await self.server.serve()
        self.session = None


class ComposeWebhookAdapter(ReverseAdapter):
    """Webhook (反向 HTTP) Adapter, 同时使用了正向 HTTP 以进行 API 调用支持"""

    tags: FrozenSet[str] = frozenset(["reverse", "http"])

    def __init__(
        self,
        broadcast: Broadcast,
        mirai_session: MiraiSession,
        route: str = "/",
        extra_headers: Optional[Dict[str, str]] = None,
        log: bool = True,
        *,
        app: Optional[FastAPI] = None,
        port: int = 8000,
        server_cls: Type[NoSigServer] = NoSigServer,
        **config_kwargs: Any,
    ):
        """初始化 ComposeWebhookAdapter

        Args:
            broadcast (Broadcast): 事件系统
            mirai_session (MiraiSession): MiraiSession 实例
            route (str, optional): 服务路径. Defaults to "/".
            extra_headers (Optional[Dict[str, str]], optional): 额外的请求头. Defaults to None.
            log (bool, optional): 是否启用连接日志. Defaults to True.
            app (Optional[FastAPI], optional): ASGI 应用. Defaults to None.
            port (int, optional): 服务端口. Defaults to 8000.
            server_cls (Type[NoSigServer], optional): Server 类. Defaults to NoSigServer.
            **config_kwargs (Any, optional): 额外配置参数. Defaults to {}.
        """
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
        self.connected: bool = False

    async def http_endpoint(self, request: Request):
        header: Dict[str, str] = dict(request.headers.items())
        if header["qq"] == str(self.mirai_session.account):
            for key, val in self.extra_headers.items():
                key = key.lower()
                if val != header.get(key, ""):
                    raise HTTPException(status_code=401, detail="Authorization Failed")
            self.connected = True
            await self.event_queue.put(self.build_event(await request.json()))
        return {"command": "", "data": {}}

    authenticate = HttpAdapter.authenticate

    async def call_api(
        self,
        action: str,
        method: CallMethod,
        data: Optional[Union[Dict[str, Any], str, FormData]] = None,
    ) -> Union[dict, list]:
        await await_predicate(lambda: self.connected)
        return await HttpAdapter.call_api(self, action, method, data)


class ReverseWebsocketAdapter(ReverseAdapter):
    """反向 WebSocket Adapter"""

    tags: FrozenSet[str] = frozenset(["reverse", "websocket"])

    def __init__(
        self,
        broadcast: Broadcast,
        mirai_session: MiraiSession,
        route: str = "/",
        extra_headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
        log: bool = True,
        *,
        app: Optional[FastAPI] = None,
        port: int = 8000,
        server_cls: Type[NoSigServer] = NoSigServer,
        **config_kwargs: Any,
    ):
        """初始化 ReverseWebsocketAdapter

        Args:
            broadcast (Broadcast): 事件系统
            mirai_session (MiraiSession): MiraiSession 实例
            route (str, optional): 服务路径. Defaults to "/".
            extra_headers (Optional[Dict[str, str]], optional): 额外的请求头. Defaults to None.
            query_params (Optional[Dict[str, str]], optional): 额外的请求参数 (在 url 中). Defaults to None.
            log (bool, optional): 是否启用连接日志. Defaults to True.
            app (Optional[FastAPI], optional): ASGI 应用. Defaults to None.
            port (int, optional): 服务端口. Defaults to 8000.
            server_cls (Type[NoSigServer], optional): Server 类. Defaults to NoSigServer.
            **config_kwargs (Any, optional): 额外配置参数. Defaults to {}.
        """
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
        self.future_map: Dict[str, asyncio.Future] = {}
        self.websocket: Optional[WebSocket] = None
        self.extra_headers: Dict[str, str] = extra_headers or {}
        self.query_params: Dict[str, str] = query_params or {}
        self.connected: bool = False

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
                sync_id: str = raw_data["syncId"] or ""
                data: dict = raw_data["data"]
                if sync_id in self.future_map:
                    fut = self.future_map.pop(sync_id)
                    res = validate_response(data)
                    if isinstance(res, Exception):
                        fut.set_exception(res)
                    else:
                        fut.set_result(res)
                else:
                    await self.event_queue.put(self.build_event(data))
                    self.connected = True
        except WebSocketDisconnect:
            self.websocket = None
            self.mirai_session.session_key = None
            self.connected = False

    async def get_session_key(self):
        if not self.mirai_session.single_mode and not self.mirai_session.session_key:
            future = self.broadcast.loop.create_future()
            self.future_map[str(id(future))] = future
            content = {
                "syncId": str(id(future)),
                "command": "verify",
                "content": {
                    "verifyKey": self.mirai_session.verify_key,
                    "qq": self.mirai_session.account,
                    "sessionKey": None,
                },
            }
            await self.websocket.send_text(json.dumps(content))
            self.mirai_session.session_key = (await future)["session"]
            logger.success("Successfully got session key")

    async def call_api(
        self,
        action: str,
        method: CallMethod,
        data: Optional[Union[Dict[str, Any], str, FormData]] = None,
    ) -> Union[dict, list]:
        await await_predicate(lambda: self.connected)
        await await_predicate(lambda: self.websocket is not None and self.mirai_session.session_key)
        future = self.broadcast.loop.create_future()
        self.future_map[str(id(future))] = future
        content = {
            "syncId": str(id(future)),
            "command": action.replace("/", "_"),
            "content": data,
        }
        if method == CallMethod.RESTGET:
            content["subCommand"] = "get"
        elif method == CallMethod.RESTPOST:
            content["subCommand"] = "update"
        elif method == CallMethod.MULTIPART:
            future.set_exception(
                NotImplementedError(f"Unsupported operation for ReverseWebsocketAdapter: {method}")
            ),
        await self.websocket.send_text(json.dumps(content, cls=DatetimeEncoder))
        return await future


class ComposeReverseWebsocketAdapter(ReverseWebsocketAdapter):
    """反向 WebSocket 与正向 HTTP 的组合 Adapter"""

    tags: FrozenSet[str] = frozenset(["reverse", "websocket", "http"])

    async def call_api(
        self, action: str, method: CallMethod, data: Optional[Union[Dict[str, Any], str, FormData]] = None
    ) -> Union[dict, list]:
        await await_predicate(lambda: self.connected)
        return await HttpAdapter.call_api(self, action, method, data)
