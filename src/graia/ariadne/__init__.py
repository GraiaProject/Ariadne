"""Ariadne

一个优雅的 QQ Bot 框架.
"""
from typing import Type

import graia.ariadne.event.lifecycle  # noqa: F401
import graia.ariadne.event.message  # noqa: F401
import graia.ariadne.event.mirai  # noqa: F401

from .app import Ariadne
from .typing import T


def get_running(type: Type[T] = Ariadne) -> T:
    """获取正在运行的实例

    Args:
        type (Type[T]): 实例类型

    Returns:
        T: 对应类型实例
    """
    from asyncio import AbstractEventLoop

    from graia.broadcast import Broadcast

    from .adapter import Adapter
    from .context import context_map

    if type in {Adapter, Ariadne, Broadcast, AbstractEventLoop}:
        if val := context_map.get(type.__name__).get(None):
            return val
    for ariadne_inst in Ariadne.running:
        if type in ariadne_inst.info:
            return ariadne_inst.info[type]
