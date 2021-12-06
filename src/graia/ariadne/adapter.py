import abc
import asyncio
import functools
import json
from asyncio.events import AbstractEventLoop
from asyncio.exceptions import CancelledError
from asyncio.locks import Event
from asyncio.queues import Queue
from asyncio.tasks import Task
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    Optional,
    Set,
    Union,
)

import aiohttp.web_exceptions
from aiohttp import ClientSession, FormData
from aiohttp.client_ws import ClientWebSocketResponse
from aiohttp.http_websocket import WSMsgType
from graia.broadcast import Broadcast
from graia.broadcast.entities.event import Dispatchable
from loguru import logger
from typing_extensions import Concatenate
from yarl import URL

from .event import MiraiEvent
from .event.network import RemoteException
from .exception import InvalidArgument, InvalidSession, NotSupportedAction
from .model import CallMethod, DatetimeEncoder, MiraiSession
from .util import await_predicate, validate_response, yield_with_timeout

if TYPE_CHECKING:
    from .typing import P, R, Self


def require_verified(
    func: "Callable[Concatenate[Adapter, P], R]",
) -> "Callable[Concatenate[Adapter, P], R]":
    @functools.wraps(func)
    def wrapper(self: "Adapter", *args: "P.args", **kwargs: "P.kwargs") -> "R":
        if not self.mirai_session.session_key:
            raise InvalidSession("you must verify the session before action.")
        return func(self, *args, **kwargs)

    return wrapper


def error_wrapper(
    network_action_callable: "Callable[Concatenate[Self, P], Awaitable[R]]",
) -> "Callable[Concatenate[Self, P], Awaitable[R]]":
    @functools.wraps(network_action_callable)
    async def wrapped_network_action_callable(self: "Adapter", *args: "P.args", **kwargs: "P.kwargs") -> "R":
        running_count = 0

        while running_count < 5:
            running_count += 1
            try:
                result = await network_action_callable(self, *args, **kwargs)
            except InvalidSession as invalid_session_exc:
                logger.error("Invalid session detected, asking daemon to restart adapter...")
                logger.exception(invalid_session_exc)
                await self.stop()
            except aiohttp.web_exceptions.HTTPNotFound:
                raise NotSupportedAction(f"{network_action_callable.__name__}: this action not supported")
            except aiohttp.web_exceptions.HTTPInternalServerError as e:
                self.broadcast.postEvent(RemoteException())
                logger.error("An exception has thrown by remote, please check the console!")
                raise
            except (
                aiohttp.web_exceptions.HTTPMethodNotAllowed,
                aiohttp.web_exceptions.HTTPRequestURITooLong,
                aiohttp.web_exceptions.HTTPTooManyRequests,
            ):

                logger.error(
                    f"It seems that we post in a wrong way "
                    f"for the action '{network_action_callable.__name__}', please open a issue."
                )
                raise
            except aiohttp.web_exceptions.HTTPRequestTimeout:
                logger.error(
                    f"timeout on {network_action_callable.__name__}, retry after 5 seconds...".format()
                )
                await asyncio.sleep(5)
                raise
            else:
                return result
        raise TimeoutError(f"Failed after 5 try on {network_action_callable.__name__}.")

    return wrapped_network_action_callable


class Adapter(abc.ABC):
    """
    适配器抽象基类.

    Args:
        broadcast(Broadcast): Broadcast 实例
        session: Session 实例, 存储了连接信息
    """

    def __init__(self, broadcast: Broadcast, mirai_session: MiraiSession, log: bool = True) -> None:
        self.broadcast = broadcast
        self.loop: AbstractEventLoop = broadcast.loop
        self.running: bool = False
        self.mirai_session: MiraiSession = mirai_session
        self.session: Optional[ClientSession] = None
        self.fetch_task: Optional[Task] = None
        self.queue: Optional[Queue[Dispatchable]] = None
        self.log: bool = log

    @abc.abstractmethod
    async def fetch_cycle(self) -> None:
        """
        负责接收并处理数据, 向事件队列发送事件.
        """
        self.running = True
        self.session = ClientSession()
        if not self.queue:
            self.queue = Queue()
        while self.running:
            await self.queue.put(Dispatchable())
        self.mirai_session.session_key = None
        await self.session.close()

    @abc.abstractmethod
    @require_verified
    @error_wrapper
    async def call_api(
        self, action: str, method: CallMethod, data: Optional[Union[dict, str]] = None
    ) -> Union[dict, list]:
        """
        向Mirai端发送数据.
        如有回复则应一并返回.

        Args:
            action (str): 要执行的操作.
            method (CallMethod): 指示对 mirai-api-http 端发送数据的方式.
            data (dict): 要发送的数据.
        Returns:
            dict: 响应字典.
        """

    async def build_event(self, data: dict) -> MiraiEvent:
        """
        从尚未明确指定事件类型的对象中获取事件的定义, 并进行解析

        Args:
            data (dict): 用 dict 表示的序列化态事件, 应包含有字段 `type` 以供分析事件定义.

        Raises:
            InvalidArgument: 目标对象中不包含字段 `type`
            ValueError: 没有找到对应的字段, 通常的, 这意味着应用获取到了一个尚未被定义的事件, 请报告问题.

        Returns:
            MiraiEvent: 已经被序列化的事件
        """
        event_type: Optional[str] = data.get("type")
        if not event_type or not isinstance(event_type, str):
            raise InvalidArgument("Unable to find 'type' field for automatic parsing")
        event_class: Optional[MiraiEvent] = self.broadcast.findEvent(event_type)  # type: ignore
        if not event_class:
            logger.error("An event is not recognized! Please report with your log to help us diagnose.")
            raise ValueError(f"Unable to find event: {event_type}", data)
        data = {k: v for k, v in data.items() if k != "type"}
        event = event_class.parse_obj(data)
        return event

    @property
    def session_activated(self) -> bool:
        return bool(self.mirai_session.session_key)

    async def start(self):
        if not self.running:
            self.fetch_task = asyncio.create_task(self.fetch_cycle())
            await await_predicate(lambda: self.running)

    async def stop(self):
        if self.running:
            self.running = False
            await self.fetch_task
            self.fetch_task = None


class HttpAdapter(Adapter):
    """
    仅使用正向 HTTP 的适配器, 采用短轮询接收事件/消息.
    不推荐.
    Note: Working In Progress
    """

    def __init__(
        self,
        broadcast: Broadcast,
        mirai_session: MiraiSession,
        fetch_interval: float = 0.5,
    ) -> None:
        super().__init__(broadcast, mirai_session)
        self.fetch_interval = fetch_interval
        raise NotImplementedError("HTTP Adapter is not supported yet!")

    async def fetch_cycle(self) -> None:
        self.running = True
        self.session = ClientSession()
        if not self.queue:
            self.queue = Queue()
        while self.running:
            await asyncio.sleep(self.fetch_interval)
        self.mirai_session.session_key = None
        await self.session.close()

    @require_verified
    @error_wrapper
    async def call_api(
        self,
        action: str,
        method: CallMethod,
        data: Optional[Union[Dict[str, Any], str]] = None,
    ) -> Union[dict, list]:
        if not data:
            data = dict()
        if not self.session:
            raise RuntimeError("Unable to get session!")

        if method == CallMethod.GET or method == CallMethod.RESTGET:
            if isinstance(data, str):
                data = json.loads(data)
            async with self.session.get(URL(self.mirai_session.url_gen(action)).with_query(data)) as response:
                response.raise_for_status()
                resp_json: dict = await response.json()

        elif method == CallMethod.POST or method == CallMethod.RESTPOST:
            if not isinstance(data, str):
                data = json.dumps(data, cls=DatetimeEncoder)
            async with self.session.post(self.mirai_session.url_gen(action), data=data) as response:
                response.raise_for_status()
                resp_json: dict = await response.json()

        else:  # MULTIPART
            form = FormData()
            if not isinstance(data, dict):
                raise ValueError("Data must be a dict in multipart call!")
            for k, v in data.items():
                form.add_fields(k, v)
            async with self.session.post(self.mirai_session.url_gen(action), data=form) as response:
                response.raise_for_status()
                resp_json: dict = await response.json()
        if "data" in resp_json:
            resp = resp_json["data"]
        else:
            resp = resp_json

        validate_response(resp)
        return resp


class WebsocketAdapter(Adapter):
    """
    仅使用正向 Websocket 的适配器.
    因 Mirai API HTTP 的实现, 部分功能不可用.
    """

    class SyncIdManager:
        allocated: Set[int] = {0}

        @classmethod
        def allocate(cls) -> int:
            new_id = max(cls.allocated) + 1
            cls.allocated.add(new_id)
            return new_id

        @classmethod
        def done(cls, sync_id: int) -> None:
            if sync_id in cls.allocated:
                cls.allocated.remove(sync_id)

    class CallResponse(Event):
        def __init__(self, *, loop: AbstractEventLoop = None) -> None:
            super().__init__(loop=loop)
            self.response: Optional[dict] = None

    def __init__(self, broadcast: Broadcast, mirai_session: MiraiSession, ping: bool = True) -> None:
        super().__init__(broadcast, mirai_session)
        self.ping = ping
        self.ping_task: Optional[Task] = None
        self.ws_conn: Optional[ClientWebSocketResponse] = None
        self.query_dict = {"verifyKey": mirai_session.verify_key}
        self.sync_event: Dict[int, WebsocketAdapter.CallResponse] = {}
        if not mirai_session.single_mode:
            self.query_dict["qq"] = mirai_session.account

    async def ws_ping(self, interval: float = 30.0) -> None:
        while self.running:
            try:
                try:
                    await self.ws_conn.ping()
                    if self.log:
                        logger.debug("websocket: ping")
                except Exception as e:
                    logger.exception(f"websocket: ping failed: {e!r}")
                else:
                    if self.log:
                        logger.debug(f"websocket: ping success, delay {interval}s")
                    await asyncio.sleep(interval)
            except asyncio.CancelledError:
                if self.log:
                    logger.debug("websocket: pinger exit")
                break

    @require_verified
    @error_wrapper
    async def call_api(
        self, action: str, method: CallMethod, data: Optional[Union[dict, str]] = None
    ) -> Union[dict, list]:
        data = data or dict()
        if not self.ws_conn:
            raise ValueError("no existing websocket connection")
        sync_id = self.SyncIdManager.allocate()
        event = self.CallResponse()
        self.sync_event[sync_id] = event
        content = {
            "syncId": sync_id,
            "command": action,
            "content": data,
        }
        if method == CallMethod.RESTGET:
            content["subCommand"] = "get"
        elif method == CallMethod.RESTPOST:
            content["subCommand"] = "update"
        elif method == CallMethod.MULTIPART:
            raise NotImplementedError(f"Unsupported operation for WebsocketAdapter: {method}")

        await self.ws_conn.send_str(json.dumps(content, cls=DatetimeEncoder))
        logger.debug(f"websocket：sent with sync id: {sync_id}")
        await event.wait()
        self.SyncIdManager.done(sync_id)
        value: dict = event.response
        del self.sync_event[sync_id]
        del event
        validate_response(value)
        if "data" in value:
            return value["data"]
        return value

    async def raw_data_parser(self, raw_data: dict) -> Optional[Dispatchable]:
        sync_id: str = raw_data["syncId"]
        received_data: dict = raw_data["data"]
        validate_response(received_data)
        if not self.mirai_session.session_key:
            if session_key := received_data.get("session", None):
                self.mirai_session.session_key = session_key
            return
        sync_id = int(sync_id)
        if sync_id not in self.SyncIdManager.allocated:
            event = await self.build_event(received_data)
            return event
        else:
            if sync_id in self.sync_event:
                response = self.sync_event[sync_id]
                response.response = received_data
                response.set()

    async def fetch_cycle(self) -> None:
        self.session = ClientSession()
        self.running = True
        if not self.queue:
            self.queue = Queue()
        async with self.session.ws_connect(
            str(URL(self.mirai_session.url_gen("all")).with_query(self.query_dict)),
            autoping=False,
        ) as connection:
            logger.info("websocket: connected")
            self.ws_conn = connection

            if self.ping:
                self.ping_task = self.loop.create_task(self.ws_ping(), name="ariadne_adapter_ws_ping")
                logger.info("websocket: ping task created")
            try:
                async for ws_message in yield_with_timeout(connection.receive, lambda: self.running):
                    if ws_message.type is WSMsgType.TEXT:
                        original_data: dict = json.loads(ws_message.data)
                        event = await self.raw_data_parser(original_data)
                        if event:
                            await self.queue.put(event)
                    elif ws_message.type is WSMsgType.CLOSED:
                        logger.warning("websocket: connection has been closed.")
                        return
                    elif ws_message.type is WSMsgType.PONG:
                        if self.log:
                            logger.debug("websocket: received pong")
                    else:
                        logger.warning("websocket: unknown message type - {}".format(ws_message.type))
            except Exception as e:
                logger.exception(e)
            finally:
                if self.ping_task:
                    self.ping_task.cancel()
                    self.ping_task = None
                    if self.log:
                        logger.debug("websocket: ping task complete")
        logger.info("websocket: disconnected")
        self.mirai_session.session_key = None
        await self.session.close()


class CombinedAdapter(Adapter):
    """
    使用正向Websocket接收事件与消息, 用HTTP发送消息/操作的适配器.
    稳定与性能的平衡, 但需要 Mirai API HTTP 同时启用 `http` 与 `ws` 适配器.

    Args:
        bcc(Broadcast): Broadcast 实例
        session: Session 实例, 存储了连接信息
        ping(bool): 是否启用 ping 功能.
    """

    def __init__(
        self, broadcast: Broadcast, mirai_session: MiraiSession, ping: bool = True, log: bool = True
    ) -> None:
        super().__init__(broadcast, mirai_session, log)
        self.ping = ping
        self.ping_task: Optional[Task] = None
        self.ws_conn: Optional[ClientWebSocketResponse] = None
        self.query_dict = {"verifyKey": mirai_session.verify_key}
        if not mirai_session.single_mode:
            self.query_dict["qq"] = mirai_session.account

    ws_ping = WebsocketAdapter.ws_ping

    call_api = HttpAdapter.call_api

    async def raw_data_parser(self, raw_data: dict) -> Optional[Dispatchable]:
        received_data = raw_data["data"]
        validate_response(received_data)
        if session_key := received_data.get("session", None):
            self.mirai_session.session_key = session_key
            return
        event = await self.build_event(received_data)
        return event

    fetch_cycle = WebsocketAdapter.fetch_cycle


DefaultAdapter = CombinedAdapter


class DebugAdapter(DefaultAdapter):
    """
    Debugging adapter
    """

    async def build_event(self, data: dict) -> MiraiEvent:
        """
        从尚未明确指定事件类型的对象中获取事件的定义, 并进行解析

        Args:
            data (dict): 用 dict 表示的序列化态事件, 应包含有字段 `type` 以供分析事件定义.

        Raises:
            InvalidArgument: 目标对象中不包含字段 `type`
            ValueError: 没有找到对应的字段, 通常的, 这意味着应用获取到了一个尚未被定义的事件, 请报告问题.

        Returns:
            MiraiEvent: 已经被序列化的事件
        """
        try:
            event = await super().build_event(data)
        except ValueError as e:
            logger.error(f"{e.args[0]}\n{json.dumps(data, indent=4)}")
            raise
        else:
            logger.debug(event)
            return event
