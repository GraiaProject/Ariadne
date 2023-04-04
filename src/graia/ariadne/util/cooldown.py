import contextlib
import inspect
import typing
from collections.abc import Hashable
from datetime import datetime, timedelta
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    AsyncGenerator,
    Awaitable,
    Callable,
    ClassVar,
    Dict,
    Generic,
    MutableMapping,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
    overload,
)
from typing_extensions import Any, TypeVar

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities.signatures import Force
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.utilles import argument_signature

from ..event.message import MessageEvent
from ..typing import generic_issubclass

T_Time = TypeVar("T_Time", timedelta, datetime, float, int, None, default=datetime)

T_SourceKey = TypeVar("T_SourceKey", bound=Hashable, default=int)

NoneType = type(None)


class CoolDown(BaseDispatcher, Generic[T_SourceKey]):
    """指示需要冷却时间才能执行操作"""

    global_source: ClassVar[Dict[str, Dict[Any, datetime]]] = {}

    source: MutableMapping[T_SourceKey, datetime]

    def __init__(
        self,
        interval: Union[int, float, timedelta],
        source: Union[MutableMapping[T_SourceKey, datetime], str, None] = None,
        override_condition: Callable[..., Union[bool, Awaitable[bool]]] = lambda: False,
        stop_on_cooldown: bool = True,
    ) -> None:
        """初始化一个冷却时间

        Args:
            interval (Union[int, float, timedelta]): 冷却时间, 单位为秒
            source (Union[MutableMapping[int, datetime], str, None], optional): 冷却映射来源, \
                为字符串时从 ClassVar 查找.
            override_condition ((...) -> Union[bool, Awaitable[bool]], optional): 超越冷却限制的条件.
            stop_on_cooldown (bool, optional): 是否在未到冷却时间时直接停止执行. Defaults to True.
        """
        self.interval = interval if isinstance(interval, timedelta) else timedelta(seconds=interval)
        self.stop_on_cooldown: bool = stop_on_cooldown
        self.override_condition: Callable[..., Union[bool, Awaitable[bool]]] = override_condition
        self.override_signature = argument_signature(self.override_condition)
        if isinstance(source, str):
            self.source = self.global_source.setdefault(source, {})
        else:
            self.source = source or {}

    async def fetch_target_key(self, event: Dispatchable) -> T_SourceKey:
        """获取目标的键，以在 source 中获取对应的冷却信息

        Args:
            event (Dispatchable): 当前事件

        Returns:
            T_SourceKey: 目标的 “冷却哈希”
        """
        if not isinstance(event, MessageEvent):
            raise ExecutionStop
        return cast(T_SourceKey, event.sender.id)

    async def get(self, target: T_SourceKey, type: Type[T_Time]) -> Tuple[T_Time, bool]:
        """获取目标的冷却信息

        Args:
            target (T_SourceKey): 目标的 “冷却哈希”
            type (Type[T_Time]): 需要返回的类型

        Returns:
            Tuple[T_Time, bool]: 第一个值是剩余的冷却时间 (或下一次可执行时间），\
                第二个值是冷却是否完成 \
                如果 type 传入的是 Optional[XXX] 则第一个值可以是 None
        """
        current_time: datetime = datetime.now()
        next_exec_time: datetime = self.source.get(target, current_time)
        delta: timedelta = next_exec_time - current_time
        satisfied: bool = delta < timedelta(seconds=0)
        if NoneType in typing.get_args(type) and delta.total_seconds() <= 0:
            result = None, satisfied
        elif generic_issubclass(datetime, type):
            result = next_exec_time, satisfied
        elif generic_issubclass(timedelta, type):
            result = delta, satisfied
        elif generic_issubclass(float, type):
            result = delta.total_seconds(), satisfied
        elif generic_issubclass(int, type):
            result = int(delta.total_seconds()), satisfied
        else:
            result = None, satisfied
        return cast(Tuple[T_Time, bool], result)

    async def set(self, target: T_SourceKey) -> None:
        """更新目标的冷却信息

        Args:
            target (T_SourceKey): 目标的 “冷却哈希”
        """
        self.source[target] = datetime.now() + self.interval

    async def beforeExecution(self, interface: DispatcherInterface[Dispatchable]):
        event = interface.event
        target_key: T_SourceKey = await self.fetch_target_key(event)
        current_time: datetime = datetime.now()
        next_exec_time: datetime = self.source.get(target_key, current_time)
        delta: timedelta = next_exec_time - current_time
        satisfied: bool = delta <= timedelta(seconds=0)
        if not satisfied and self.stop_on_cooldown:
            param_dict: Dict[str, Any] = {}
            for name, anno, _ in self.override_signature:
                param_dict[name] = await interface.lookup_param(name, anno, None)
            res = self.override_condition(**param_dict)
            if not ((await res) if inspect.isawaitable(res) else res):
                raise ExecutionStop
        interface.local_storage[f"{__name__}:next_exec_time"] = next_exec_time
        interface.local_storage[f"{__name__}:delta"] = delta

    async def catch(self, interface: DispatcherInterface[Dispatchable]):
        annotation = interface.annotation
        next_exec_time: datetime = interface.local_storage[f"{__name__}:next_exec_time"]
        delta: timedelta = interface.local_storage[f"{__name__}:delta"]
        if NoneType in typing.get_args(annotation) and delta.total_seconds() <= 0:
            return Force(None)
        if generic_issubclass(datetime, annotation):
            return next_exec_time
        if generic_issubclass(timedelta, annotation):
            return delta
        if generic_issubclass(float, annotation):
            return delta.total_seconds()
        if generic_issubclass(int, annotation):
            return int(delta.total_seconds())

    async def afterDispatch(
        self,
        interface: DispatcherInterface[Dispatchable],
        exception: Optional[Exception],
        _: Optional[TracebackType],
    ):
        if not exception:
            event = interface.event
            await self.set(await self.fetch_target_key(event))

    if TYPE_CHECKING:

        @overload
        @contextlib.asynccontextmanager
        async def trigger(self, target: int) -> AsyncGenerator[Tuple[Optional[datetime], bool], None]:
            ...

        @overload
        @contextlib.asynccontextmanager
        async def trigger(self, target: int, type: Type[T_Time]) -> AsyncGenerator[Tuple[T_Time, bool], None]:
            ...

    @contextlib.asynccontextmanager
    async def trigger(
        self, target: T_SourceKey, type: Type[T_Time]
    ) -> AsyncGenerator[Tuple[T_Time, bool], None]:
        """触发冷却。

        Args:
            target (T_SourceKey): 目标的 “冷却哈希”
            type (Type[T_Time]): 需要返回的类型
        """
        try:
            yield await self.get(target, type)
        except Exception as e:
            raise e
        else:
            await self.set(target)
