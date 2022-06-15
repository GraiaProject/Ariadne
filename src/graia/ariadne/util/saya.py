from __future__ import annotations

import functools
import inspect
from typing import Callable, Dict, Generic, List, Type, Union, overload

from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.typing import T_Dispatcher
from graia.saya import Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.saya.cube import Cube

from ..typing import P, R
from ..util import gen_subclass


class AttachedCallable(Generic[P, R]):
    func: Callable[P, R]
    dispatchers: List[T_Dispatcher]
    decorators: Dict[str, Decorator]
    headless_decorators: List[Decorator]

    def __init__(self, obj: Union[Callable[P, R], AttachedCallable[P, R]]) -> None:
        if isinstance(obj, AttachedCallable):
            self.__dict__ = obj.__dict__
        else:
            self.dispatchers = []
            self.decorators = {}
            self.headless_decorators = []
            self.func: Callable[P, R] = obj
            functools.update_wrapper(self, self.func)

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> R:
        return self.func(*args, **kwds)

    @property
    def __signature__(self) -> inspect.Signature:
        sig: inspect.Signature = inspect.signature(self.func)
        for k, d in self.decorators.items():
            sig.parameters[k].__setattr__("_default", d)
        return sig


def dispatch(*dispatcher: T_Dispatcher) -> Callable[[Callable[P, R]], AttachedCallable[P, R]]:
    """附加参数解析器，最后必须接 `listen` 才能起效

    Args:
        *dispatcher (T_Dispatcher): 参数解析器

    Returns:
        Callable[[Callable[P, R]], AttachedCallable[P, R]]: 装饰器
    """

    def wrapper(func: Callable[P, R]) -> AttachedCallable[P, R]:
        attached = AttachedCallable(func)
        attached.dispatchers.extend(dispatcher)
        return attached

    return wrapper


@overload
def decorate(*decorator: Decorator) -> Callable[[Callable[P, R]], AttachedCallable[P, R]]:
    """附加多个无头装饰器

    Args:
        *decorator (Decorator): 无头装饰器

    Returns:
        Callable[[Callable[P, R]], AttachedCallable[P, R]]: 装饰器
    """
    ...


@overload
def decorate(name: str, decorator: Decorator, /) -> Callable[[Callable[P, R]], AttachedCallable[P, R]]:
    """给指定参数名称附加装饰器

    Args:
        name (str): 参数名称
        decorator (Decorator): 装饰器

    Returns:
        Callable[[Callable[P, R]], AttachedCallable[P, R]]: 装饰器
    """
    ...


@overload
def decorate(map: Dict[str, Decorator], /) -> Callable[[Callable[P, R]], AttachedCallable[P, R]]:
    """给指定参数名称附加装饰器

    Args:
        map (Dict[str, Decorator]): 参数名称与装饰器的映射

    Returns:
        Callable[[Callable[P, R]], AttachedCallable[P, R]]: 装饰器
    """
    ...


def decorate(*args) -> Callable[[Callable[P, R]], AttachedCallable[P, R]]:
    def wrapper(func: Callable[P, R]) -> AttachedCallable[P, R]:
        attached = AttachedCallable(func)
        if isinstance(args[0], str):
            name: str = args[0]
            decorator: Decorator = args[1]
            attached.decorators[name] = decorator
        elif isinstance(args[0], dict):
            attached.decorators.update(args[0])
        else:
            attached.headless_decorators.extend(args)
        return attached

    return wrapper


def listen(
    *event: Union[Type[Dispatchable], str], priority: int = 16
) -> Callable[[Callable[P, R]], AttachedCallable[P, R]]:
    """在当前 Saya Channel 中监听指定事件

    Args:
        *event (Union[Type[Dispatchable], str]): 事件类型或事件名称
        priority (int, optional): 事件优先级, 越小越优先

    Returns:
        Callable[[Callable[P, R]], AttachedCallable[P, R]]: 装饰器
    """
    EVENTS: Dict[str, Type[Dispatchable]] = {e.__name__: e for e in gen_subclass(Dispatchable)}
    events: List[Type[Dispatchable]] = [e if isinstance(e, type) else EVENTS[e] for e in event]

    def wrapper(func: Callable[P, R]) -> AttachedCallable[P, R]:
        attached = AttachedCallable(func)
        channel = Channel.current()
        channel.content.append(
            Cube(
                attached,
                ListenerSchema(events, None, attached.dispatchers, attached.headless_decorators, priority),
            )
        )
        return attached

    return wrapper
