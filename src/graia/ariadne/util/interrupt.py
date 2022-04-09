from typing import Callable, Generic, List, Optional, Type, TypeVar, cast

from graia.broadcast import Broadcast
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interrupt import InterruptControl, Waiter
from graia.broadcast.typing import T_Dispatcher

from .. import get_running
from ..typing import T


class FunctionWaiter(Waiter, Generic[T]):
    """将 Waiter.create_using_function 封装了一层"""

    def __init__(
        self,
        func: Callable[..., T],
        events: List[Type[Dispatchable]],
        dispatchers: Optional[List[T_Dispatcher]] = None,
        decorators: Optional[List[Decorator]] = None,
        priority: int = 15,
    ) -> None:
        self.listening_events = self.events = events
        self.using_dispatchers = self.dispatchers = dispatchers or []
        self.using_decorators = self.decorators = decorators or []
        self.priority = priority
        self.detected_event = func  # type: ignore

    async def wait(
        self,
        timeout: Optional[float] = None,
    ) -> T:
        inc: InterruptControl = InterruptControl(get_running(Broadcast))
        return await inc.wait(
            self,
            timeout=timeout,  # type: ignore
        )


T_E = TypeVar("T_E", bound=Dispatchable)


class EventWaiter(Waiter, Generic[T_E]):
    """将 Waiter.create_using_event 封装了一层"""

    def __init__(
        self,
        event: Type[T_E],
        dispatchers: Optional[List[T_Dispatcher]] = None,
        decorators: Optional[List[Decorator]] = None,
        extra_validator: Optional[Callable[[T_E], bool]] = None,
        priority: int = 15,
    ) -> None:
        self.events = [event]
        self.listening_events = cast(List[Type[Dispatchable]], self.events)
        self.using_dispatchers = self.dispatchers = dispatchers or []
        self.using_decorators = self.decorators = decorators or []
        self.extra_validator = extra_validator
        self.priority = priority

    async def detected_event(self, ev: Dispatchable) -> T_E:
        event = cast(T_E, ev)
        if self.extra_validator and not self.extra_validator(event):
            raise ExecutionStop
        return event

    async def wait(
        self,
        timeout: Optional[float] = None,
    ) -> T_E:
        inc: InterruptControl = InterruptControl(get_running(Broadcast))
        return await inc.wait(
            self,
            timeout=timeout,  # type: ignore
        )
