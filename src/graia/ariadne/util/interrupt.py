from typing import Awaitable, Callable, Generic, List, Optional, Type, TypeVar, cast

from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interrupt import InterruptControl, Waiter
from graia.broadcast.typing import T_Dispatcher

from ..app import Ariadne
from ..typing import T


class FunctionWaiter(Waiter, Generic[T]):
    """将 Waiter.create_using_function 封装了一层"""

    def __init__(
        self,
        func: Callable[..., Awaitable[Optional[T]]],
        events: List[Type[Dispatchable]],
        dispatchers: Optional[List[T_Dispatcher]] = None,
        decorators: Optional[List[Decorator]] = None,
        priority: int = 15,
        block_propagation: bool = False,
    ) -> None:
        """
        Args:
            func (Callable): 调用函数
            events (List[Type[Dispatchable]]): 事件类型
            dispatchers (Optional[List[T_Dispatcher]]): 广播器
            decorators (Optional[List[Decorator]]): 装饰器
            priority (int): 优先级
            block_propagation (bool): 是否阻止事件往下传播
        """
        self.listening_events = self.events = events
        self.using_dispatchers = self.dispatchers = dispatchers or []
        self.using_decorators = self.decorators = decorators or []
        self.priority = priority
        self.block_propagation = block_propagation
        self.detected_event = func  # type: ignore

    async def wait(
        self,
        timeout: Optional[float] = None,
    ) -> T:
        inc: InterruptControl = InterruptControl(Ariadne.service.broadcast)
        return await inc.wait(
            self,
            timeout=timeout,  # type: ignore
        )


T_E = TypeVar("T_E", bound=Dispatchable)


class EventWaiter(Waiter, Generic[T_E]):
    """将 Waiter.create_using_event 封装了一层"""

    def __init__(
        self,
        events: List[Type[T_E]],
        dispatchers: Optional[List[T_Dispatcher]] = None,
        decorators: Optional[List[Decorator]] = None,
        extra_validator: Optional[Callable[[T_E], bool]] = None,
        priority: int = 15,
        block_propagation: bool = False,
    ) -> None:
        """
        Args:
            events (List[Type[T_E]]): 事件类型
            dispatchers (Optional[List[T_Dispatcher]], optional): Dispatcher 列表
            decorators (Optional[List[Decorator]], optional): Decorator 列表
            extra_validator (Optional[Callable[[T_E], bool]], optional): 额外的验证器
            priority (int, optional): 优先级, 越小越靠前
            block_propagation (bool): 是否阻止事件往下传播
        """
        self.events = events
        self.listening_events = cast(List[Type[Dispatchable]], self.events)
        self.using_dispatchers = self.dispatchers = dispatchers or []
        self.using_decorators = self.decorators = decorators or []
        self.extra_validator = extra_validator
        self.priority = priority
        self.block_propagation = block_propagation

    async def detected_event(self, ev: Dispatchable) -> T_E:
        event = cast(T_E, ev)
        if self.extra_validator and not self.extra_validator(event):
            raise ExecutionStop
        return event

    async def wait(
        self,
        timeout: Optional[float] = None,
    ) -> T_E:
        inc: InterruptControl = InterruptControl(Ariadne.service.broadcast)
        return await inc.wait(
            self,
            timeout=timeout,  # type: ignore
        )
