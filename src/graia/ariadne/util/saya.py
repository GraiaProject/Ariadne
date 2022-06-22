from __future__ import annotations

import inspect
from typing import Callable, Dict, List, Optional, Type, Union, overload

from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.typing import T_Dispatcher
from graia.saya import Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.saya.cube import Cube

from ..typing import T_Callable, Wrapper
from ..util import gen_subclass


def ensure_cube_as_listener(func: Callable) -> Cube[ListenerSchema]:
    if hasattr(func, "__cube__"):
        if not isinstance(func.__cube__.metaclass, ListenerSchema):
            raise TypeError("Cube must be ListenerSchema")
        return func.__cube__
    channel = Channel.current()
    for cube in channel.content:
        if cube.content is func and isinstance(cube.metaclass, ListenerSchema):
            func.__cube__ = cube
            break
    else:
        cube = Cube(func, ListenerSchema([], None, [], [], 16))
        channel.content.append(cube)
        func.__cube__ = cube
    return func.__cube__


def dispatch(*dispatcher: T_Dispatcher) -> Wrapper:
    """附加参数解析器，最后必须接 `listen` 才能起效

    Args:
        *dispatcher (T_Dispatcher): 参数解析器

    Returns:
        Callable[[T_Callable], T_Callable]: 装饰器
    """

    def wrapper(func: T_Callable) -> T_Callable:
        cube: Cube[ListenerSchema] = ensure_cube_as_listener(func)
        cube.metaclass.inline_dispatchers.extend(dispatcher)
        return func

    return wrapper


@overload
def decorate(*decorator: Decorator) -> Wrapper:
    """附加多个无头装饰器

    Args:
        *decorator (Decorator): 无头装饰器

    Returns:
        Callable[[T_Callable], T_Callable]: 装饰器
    """
    ...


@overload
def decorate(name: str, decorator: Decorator, /) -> Wrapper:
    """给指定参数名称附加装饰器

    Args:
        name (str): 参数名称
        decorator (Decorator): 装饰器

    Returns:
        Callable[[T_Callable], T_Callable]: 装饰器
    """
    ...


@overload
def decorate(map: Dict[str, Decorator], /) -> Wrapper:
    """给指定参数名称附加装饰器

    Args:
        map (Dict[str, Decorator]): 参数名称与装饰器的映射

    Returns:
        Callable[[T_Callable], T_Callable]: 装饰器
    """
    ...


def decorate(*args) -> Wrapper:
    arg: Union[Dict[str, Decorator], List[Decorator]]
    if isinstance(args[0], str):
        name: str = args[0]
        decorator: Decorator = args[1]
        arg = {name: decorator}
    elif isinstance(args[0], dict):
        arg = args[0]
    else:
        arg = list(args)

    def wrapper(func: T_Callable) -> T_Callable:
        cube = ensure_cube_as_listener(func)
        if isinstance(arg, list):
            cube.metaclass.decorators.extend(arg)
        elif isinstance(arg, dict):
            sig = inspect.signature(func)
            sig.parameters
            for param in sig.parameters.values():
                if param.name in arg:
                    setattr(param, "_default", arg[param.name])
        return func

    return wrapper


def listen(*event: Union[Type[Dispatchable], str]) -> Wrapper:
    """在当前 Saya Channel 中监听指定事件

    Args:
        *event (Union[Type[Dispatchable], str]): 事件类型或事件名称
        priority (int, optional): 事件优先级, 越小越优先

    Returns:
        Callable[[T_Callable], T_Callable]: 装饰器
    """
    EVENTS: Dict[str, Type[Dispatchable]] = {e.__name__: e for e in gen_subclass(Dispatchable)}
    events: List[Type[Dispatchable]] = [e if isinstance(e, type) else EVENTS[e] for e in event]

    def wrapper(func: T_Callable) -> T_Callable:
        cube = ensure_cube_as_listener(func)
        cube.metaclass.listening_events.extend(events)
        return func

    return wrapper


def priority(priority: int, *events: Type[Dispatchable]) -> Wrapper:
    """设置事件优先级

    Args:
        priority (int): 事件优先级
        *events (Type[Dispatchable]): 提供时则会设置这些事件的优先级, 否则设置全局优先级

    Returns:
        Callable[[T_Callable], T_Callable]: 装饰器
    """

    def wrapper(func: T_Callable) -> T_Callable:
        cube = ensure_cube_as_listener(func)
        cube.metaclass.priority = priority
        if events:
            extra: Dict[Optional[Type[Dispatchable]], int] = getattr(cube.metaclass, "extra_priorities", {})
            extra.update((e, priority) for e in events)
        return func

    return wrapper
