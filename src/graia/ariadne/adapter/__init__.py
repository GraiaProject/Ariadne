"""Ariadne 的适配器"""
import abc
import asyncio
import json
from asyncio import Future, Queue, Task
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type, TypeVar, Union

from aiohttp import ClientSession, FormData
from graia.broadcast import Broadcast
from loguru import logger

from graia.ariadne.util import await_predicate

from ..event import MiraiEvent
from ..exception import InvalidArgument
from ..model import CallMethod, MiraiSession


@dataclass
class APICallInfo:
    action: str
    method: CallMethod
    data: Union[Dict[str, Any], str, FormData]
    meta: bool
    future: Future


class Adapter(abc.ABC):
    def __init__(self, broadcast: Broadcast, mirai_session: MiraiSession) -> None:
        """初始化 Adapter.

        Args:
            broadcast (Broadcast): 广播系统
            mirai_session (MiraiSession): MiraiSession 实例
            log (bool, optional): 开启网络连接日志. Defaults to False.
        """
        self.broadcast: Broadcast = broadcast
        self.running: bool = False
        self.mirai_session: MiraiSession = mirai_session
        self.fetch_task: Optional[Task] = None
        self.call_task: Optional[Task] = None
        self.session: Optional[ClientSession] = None
        self.event_queue: Optional[Queue[MiraiEvent]] = None
        self.call_queue: Optional[Queue[APICallInfo]] = None

    async def call_api(
        self,
        action: str,
        method: CallMethod,
        data: Optional[Union[Dict[str, Any], str, FormData]] = None,
        meta: bool = False,
    ) -> Union[dict, list]:
        future: Future = self.broadcast.loop.create_future()
        await self.call_queue.put(APICallInfo(action, method, data or {}, meta, future))
        return await future

    async def start(self):
        if not self.running:
            self.running = True
            self.call_queue = Queue()
            self.event_queue = Queue()
            self.call_task = asyncio.create_task(self.call_cycle())
            self.fetch_task = asyncio.create_task(self.fetch_cycle())
        if not isinstance(self, ReverseAdapter):
            await await_predicate(lambda: self.mirai_session.session_key or self.mirai_session.single_mode)

    def build_event(self, data: dict) -> MiraiEvent:
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

    @abc.abstractmethod
    async def fetch_cycle(self):
        ...

    @abc.abstractmethod
    async def call_cycle(self):
        ...

    async def stop(self):
        """停止 Adapter"""
        self.running = False
        await self.fetch_task
        logger.success("Event fetch task completed.")
        await self.call_task
        logger.success("Caller task completed.")
        self.session = None
        self.fetch_task = None
        self.call_task = None


from .forward import HttpAdapter as HttpAdapter  # noqa: F401, E402
from .forward import WebsocketAdapter as WebsocketAdapter  # noqa: F401, E402

try:
    from .reverse import ReverseAdapter as ReverseAdapter  # noqa: F401, E402
    from .reverse import (  # noqa: F401, E402
        ReverseWebsocketAdapter as ReverseWebsocketAdapter,
    )
    from .reverse import WebhookAdapter as WebhookAdapter  # noqa: F401, E402
except ImportError:
    ReverseAdapter = type("ReverseAdapter", (Adapter,), {})

T_Adapter = TypeVar("T_Adapter", bound=Type[Adapter])


class CombineMeta(type):
    def __getitem__(mcs, combine: T_Adapter) -> T_Adapter:
        return type(
            f"Http+{combine.__name__}Adapter",
            (combine,),
            {
                "__module__": combine.__module__,
                "authenticate": HttpAdapter.authenticate,
                "call_cycle": HttpAdapter.call_cycle,
            },
        )


class Combine(metaclass=CombineMeta):
    pass


DefaultAdapter = Combine[WebsocketAdapter]


class DebugAdapter(DefaultAdapter):
    """
    Debugging adapter
    """

    def build_event(self, data: dict) -> MiraiEvent:
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
            event = super().build_event(data)
        except ValueError as e:
            logger.error(f"{e.args[0]}\n{json.dumps(data, indent=4)}")
            raise
        else:
            logger.debug(event)
            return event
