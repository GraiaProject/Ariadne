import builtins
import contextlib
import inspect
import typing
from datetime import datetime, timedelta
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    MutableMapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.signatures import Force
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.utilles import argument_signature

from graia.ariadne.typing import generic_issubclass

from ..event.message import MessageEvent

T_Time = TypeVar("T_Time", timedelta, datetime, float, int)


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

    async def get(self, target: int, type: Type[T_Time]) -> Tuple[Optional[T_Time], bool]:
        current_time: datetime = datetime.now()
        next_exec_time: datetime = self.source.get(target, current_time)
        delta: timedelta = next_exec_time - current_time
        satisfied: bool = delta < timedelta(seconds=0)
        if builtins.type(None) in typing.get_args(type) and delta.total_seconds() <= 0:
            return None, satisfied
        if generic_issubclass(datetime, type):
            return next_exec_time, satisfied  # type: ignore
        if generic_issubclass(timedelta, type):
            return delta, satisfied  # type: ignore
        if generic_issubclass(float, type):
            return delta.total_seconds(), satisfied  # type: ignore
        if generic_issubclass(int, type):
            return int(delta.total_seconds()), satisfied  # type: ignore
        return None, satisfied

    async def set(self, target: int) -> None:
        self.source[target] = datetime.now() + self.interval

    async def beforeExecution(self, interface: DispatcherInterface[MessageEvent]):
        event = interface.event
        sender_id = event.sender.id
        current_time: datetime = datetime.now()
        next_exec_time: datetime = self.source.get(sender_id, current_time)
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

    async def catch(self, interface: DispatcherInterface[MessageEvent]):
        annotation = interface.annotation
        next_exec_time: datetime = interface.local_storage[f"{__name__}:next_exec_time"]
        delta: timedelta = interface.local_storage[f"{__name__}:delta"]
        if builtins.type(None) in typing.get_args(annotation) and delta.total_seconds() <= 0:
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
        interface: DispatcherInterface[MessageEvent],
        exception: Optional[Exception],
        _: Optional[TracebackType],
    ):
        event = interface.event
        sender_id = event.sender.id
        if not exception:
            await self.set(sender_id)

    if TYPE_CHECKING:

        @overload
        @contextlib.asynccontextmanager
        async def trigger(self, target: int) -> AsyncGenerator[Tuple[Optional[datetime], bool], None]:
            ...

        @overload
        @contextlib.asynccontextmanager
        async def trigger(
            self, target: int, type: Type[T_Time]
        ) -> AsyncGenerator[Tuple[Optional[T_Time], bool], None]:
            ...

    @contextlib.asynccontextmanager
    async def trigger(
        self, target: int, type: Type[T_Time] = datetime
    ) -> AsyncGenerator[Tuple[Union[T_Time, datetime, None], bool], None]:
        try:
            yield await self.get(target, type)
        except:  # noqa
            raise
        else:
            await self.set(target)
