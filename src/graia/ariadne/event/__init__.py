"""Ariadne 的事件"""
from graia.broadcast import Dispatchable

from ..dispatcher import BaseDispatcher
from ..model import AriadneBaseModel


class MiraiEvent(Dispatchable, AriadneBaseModel):
    """Ariadne 的事件基类"""

    type: str
    """事件类型"""

    Dispatcher = BaseDispatcher


from . import lifecycle as lifecycle  # noqa: F401, E402
from . import message as message  # noqa: F401, E402
from . import mirai as mirai  # noqa: F401, E402
