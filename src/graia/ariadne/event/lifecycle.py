import typing

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

if typing.TYPE_CHECKING:
    from graia.ariadne.app import Ariadne


class ApplicationLifecycleEvent(Dispatchable):
    """
    指示有关应用 (Ariadne) 的事件.
    """

    app: "Ariadne"

    def __init__(self, app) -> None:
        self.app = app

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: "DispatcherInterface[ApplicationLifecycleEvent]"):
            from ..app import Ariadne

            if interface.annotation is Ariadne:
                return interface.event.app


class ApplicationLaunched(ApplicationLifecycleEvent):
    """
    指示 Ariadne 启动.
    """


class ApplicationShutdowned(ApplicationLifecycleEvent):
    """
    指示 Ariadne 关闭.
    """
