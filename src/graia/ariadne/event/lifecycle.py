"""Ariadne, Adapter 生命周期相关事件"""

import typing

from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from ..dispatcher import BaseDispatcher
from ..typing import generic_issubclass

if typing.TYPE_CHECKING:
    from ..app import Ariadne


class ApplicationLifecycleEvent(Dispatchable):
    """指示有关应用 (Ariadne) 的事件."""

    app: "Ariadne"

    def __init__(self, app: "Ariadne") -> None:
        self.app = app

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface"):
            from ..app import Ariadne

            if isinstance(interface.event, ApplicationLifecycleEvent) and generic_issubclass(
                Ariadne, interface.annotation
            ):
                return interface.event.app


class ApplicationLaunch(ApplicationLifecycleEvent):
    """指示 Ariadne 启动."""


class ApplicationShutdown(ApplicationLifecycleEvent):
    """指示 Ariadne 关闭."""


ApplicationLaunched = ApplicationLaunch
ApplicationShutdowned = ApplicationShutdown


class AccountLaunch(ApplicationLifecycleEvent):
    """指示账号的链接已启动."""


class AccountShutdown(ApplicationLifecycleEvent):
    """指示账号的链接关闭."""


class AccountConnectionFail(ApplicationLifecycleEvent):
    """和 mirai-api-http 的链接断开，不论是因为连接失败还是配置失败"""
