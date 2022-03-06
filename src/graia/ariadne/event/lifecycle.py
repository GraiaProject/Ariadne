"""Ariadne, Adapter 生命周期相关事件"""
import typing

from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from ..dispatcher import BaseDispatcher
from ..typing import generic_issubclass

if typing.TYPE_CHECKING:
    from ..app import Ariadne


class ApplicationLifecycleEvent(Dispatchable):
    """
    指示有关应用 (Ariadne) 的事件.
    """

    app: "Ariadne"

    def __init__(self, app: "Ariadne") -> None:
        self.app = app

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            from ..app import Ariadne

            if isinstance(interface.event, ApplicationLifecycleEvent):
                if generic_issubclass(Ariadne, interface.annotation):
                    return interface.event.app


class ApplicationLaunched(ApplicationLifecycleEvent):
    """
    指示 Ariadne 启动.
    """


class ApplicationShutdowned(ApplicationLifecycleEvent):
    """
    指示 Ariadne 关闭.
    """


class AdapterLaunched(ApplicationLifecycleEvent):
    """
    指示远程适配器启动了.
    """


class AdapterShutdowned(ApplicationLifecycleEvent):
    """
    指示远程适配器关闭了.
    """
