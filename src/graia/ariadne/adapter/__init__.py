"""Ariadne 的适配器"""
import abc
import asyncio
from asyncio import Queue, Task
from typing import Any, Dict, FrozenSet, Optional, Union

from aiohttp import ClientSession, FormData
from graia.broadcast import Broadcast
from loguru import logger

from graia.ariadne.util import await_predicate

from ..event import MiraiEvent
from ..exception import InvalidArgument
from ..model import CallMethod, MiraiSession


class Adapter(abc.ABC):

    tags: FrozenSet[str] = frozenset(["abstract"])

    def __init__(self, broadcast: Broadcast, mirai_session: MiraiSession) -> None:
        """初始化 Adapter.

        Args:
            broadcast (Broadcast): 广播系统
            mirai_session (MiraiSession): MiraiSession 实例
        """
        self.broadcast: Broadcast = broadcast
        self.running: bool = False
        self.mirai_session: MiraiSession = mirai_session
        self.fetch_task: Optional[Task] = None
        self.call_task: Optional[Task] = None
        self.session: Optional[ClientSession] = None
        self.event_queue: Optional[Queue[MiraiEvent]] = None
        if "abstract" in self.tags:
            raise TypeError("Adapter is abstract, cannot be instantiated.")

    @abc.abstractmethod
    async def call_api(
        self,
        action: str,
        method: CallMethod,
        data: Optional[Union[Dict[str, Any], str, FormData]] = None,
    ) -> Union[dict, list]:
        """调用 API

        Args:
            action (str): API 动作名, 用斜杠分割
            method (CallMethod): 调用方法
            data (Optional[Union[Dict[str, Any], str, FormData]], optional): 调用数据. Defaults to None.

        Returns:
            Union[dict, list]: API 返回的数据, 为 json 兼容格式
        """
        ...

    async def start(self):
        """启动 Adapter"""
        if not self.running:
            self.running = True
            self.event_queue = Queue()
            self.fetch_task = asyncio.create_task(self.fetch_cycle())
        if "reverse" not in self.tags:
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
        """循环获取事件, 放入 event_queue 中"""
        ...

    async def stop(self):
        """停止 Adapter"""
        self.running = False
        await self.fetch_task
        logger.success("Event fetch task completed.")
        self.fetch_task = None


from .forward import ComposeForwardAdapter as ComposeForwardAdapter  # noqa: F401, E402
from .forward import HttpAdapter as HttpAdapter  # noqa: F401, E402
from .forward import WebsocketAdapter as WebsocketAdapter  # noqa: F401, E402

DefaultAdapter = ComposeForwardAdapter


class DebugAdapter(DefaultAdapter):
    """调试 Adapter"""

    def build_event(self, data: dict) -> MiraiEvent:
        event = super().build_event(data)
        logger.debug(event)
        return event


try:
    from .reverse import (  # noqa: F401, E402
        ComposeReverseWebsocketAdapter as ComposeReverseWebsocketAdapter,
    )
    from .reverse import (  # noqa: F401, E402
        ComposeWebhookAdapter as ComposeWebhookAdapter,
    )
    from .reverse import ReverseAdapter as ReverseAdapter  # noqa: F401, E402
    from .reverse import (  # noqa: F401, E402
        ReverseWebsocketAdapter as ReverseWebsocketAdapter,
    )
except ImportError:
    pass
