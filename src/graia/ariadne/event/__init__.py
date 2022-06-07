"""Ariadne 的事件"""
from graia.broadcast import Dispatchable
from pydantic import validator

from ..dispatcher import BaseDispatcher
from ..exception import InvalidEventTypeDefinition
from ..model import AriadneBaseModel
from ..util import AttrConvertMixin


class MiraiEvent(Dispatchable, AriadneBaseModel, AttrConvertMixin):
    """Ariadne 的事件基类"""

    type: str
    """事件类型"""

    @validator("type", allow_reuse=True)
    def validate_event_type(cls, v):
        """验证事件类型, 通过比对 type 字段实现"""
        if not isinstance(cls, type):
            raise TypeError("cls must be a class!")
        if cls.type != v:
            raise InvalidEventTypeDefinition(f"{cls.__name__}'s type must be '{cls.type}', not '{v}'")
        return v

    Dispatcher = BaseDispatcher


from . import lifecycle as lifecycle  # noqa: F401, E402
from . import message as message  # noqa: F401, E402
from . import mirai as mirai  # noqa: F401, E402
