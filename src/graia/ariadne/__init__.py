"""Ariadne

一个优雅的 QQ Bot 框架.
"""
from typing import Literal, Optional, Type, overload

import graia.ariadne.event.lifecycle  # noqa: F401
import graia.ariadne.event.message  # noqa: F401
import graia.ariadne.event.mirai  # noqa: F401

from .app import Ariadne
from .typing import T


@overload
def get_running(type: Type[T] = Ariadne) -> T:
    ...


@overload
def get_running(type: Type[T], fail_err: Literal[False]) -> Optional[T]:
    ...


@overload
def get_running(type: Type[T], fail_err: Literal[True]) -> T:
    ...


def get_running(type: Type[T] = Ariadne, fail_err: bool = True) -> Optional[T]:
    """获取正在运行的实例

    Args:
        type (Type[T]): 实例类型
        fail_err (bool, optional): 如果没有正在运行的实例, 是否抛出异常

    Returns:
        T: 对应类型实例
    """
    from asyncio import AbstractEventLoop

    from graia.broadcast import Broadcast

    from .adapter import Adapter
    from .context import context_map

    if type in {Adapter, Ariadne, Broadcast, AbstractEventLoop}:
        if ctx := context_map.get(type.__name__):
            if val := ctx.get(None):
                return val
    for ariadne_inst in Ariadne.running:
        if type in ariadne_inst.info:
            return ariadne_inst.info[type]  # type: ignore
    if fail_err:
        raise ValueError(f"{type.__name__} is not running")
    return None
