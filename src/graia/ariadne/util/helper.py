import inspect
import typing
from datetime import datetime, timedelta
from types import TracebackType
from typing import Any, Awaitable, Callable, Dict, MutableMapping, Optional, Union

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.signatures import Force
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.utilles import argument_signature

from ..event.message import MessageEvent


class CoolDown(BaseDispatcher):
    """指示需要冷却时间才能执行操作"""

    global_source: Dict[str, Dict[int, datetime]] = {}

    def __init__(
        self,
        interval: Union[int, float, timedelta],
        source: Union[MutableMapping[int, datetime], str, None] = None,
        override_condition: Callable[..., Union[bool, Awaitable[bool]]] = lambda: False,
        stop_on_cooldown: bool = True,
    ) -> None:
        """初始化一个冷却时间

        Args:
            interval (Union[int, float, timedelta]): 冷却时间, 单位为秒
            source (Union[MutableMapping[int, datetime], str, None], optional): 冷却映射来源, 为字符串时从 ClassVar 查找.
            override_condition ((...) -> Union[bool, Awaitable[bool]], optional): 超越冷却限制的条件.
            stop_on_cooldown (bool, optional): 是否在未到冷却时间时直接停止执行. Defaults to True.
        """
        self.interval = interval if isinstance(interval, timedelta) else timedelta(seconds=interval)
        self.stop_on_cooldown: bool = stop_on_cooldown
        self.override_condition: Callable[..., Union[bool, Awaitable[bool]]] = override_condition
        self.override_signature = argument_signature(self.override_condition)
        if isinstance(source, str):
            self.source: MutableMapping[int, datetime] = self.global_source.setdefault(source, {})
        else:
            self.source: MutableMapping[int, datetime] = source or {}

    async def beforeExecution(self, interface: DispatcherInterface[MessageEvent]):
        event = interface.event
        sender_id = event.sender.id
        next_exec_time = self.source.get(sender_id, datetime.now())
        current_time = datetime.now()
        if current_time < next_exec_time:
            if self.stop_on_cooldown:
                param_dict: Dict[str, Any] = {}
                for name, anno, _ in self.override_signature:
                    param_dict[name] = await interface.lookup_param(name, anno, None)
                res = self.override_condition(**param_dict)
                if not (await res) if inspect.isawaitable(res) else res:
                    raise ExecutionStop

        interface.local_storage["current_time"] = current_time
        interface.local_storage["next_exec_time"] = next_exec_time

    async def catch(self, interface: DispatcherInterface[MessageEvent]):
        current_time: datetime = interface.local_storage.get("current_time")
        next_exec_time: datetime = interface.local_storage.get("next_exec_time")
        if (
            current_time >= next_exec_time
            and typing.get_origin(interface.annotation) is Union
            and type(None) in typing.get_args(interface.annotation)
        ):
            return Force(None)
        anno = typing.get_args(interface.annotation) or (interface.annotation,)
        if timedelta in anno:
            return next_exec_time - current_time
        elif datetime in anno:
            return next_exec_time
        elif float in anno:
            return next_exec_time.timestamp() - current_time.timestamp()
        elif int in anno:
            return int(next_exec_time.timestamp() - current_time.timestamp())

    async def afterDispatch(
        self,
        interface: DispatcherInterface[MessageEvent],
        exception: Optional[Exception],
        _: Optional[TracebackType],
    ):
        event = interface.event
        sender_id = event.sender.id
        if not exception:
            self.source[sender_id] = datetime.now() + self.interval
