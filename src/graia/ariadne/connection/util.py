from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Literal, overload

from loguru import logger

from ..exception import (
    AccountMuted,
    AccountNotFound,
    InvalidArgument,
    InvalidSession,
    InvalidVerifyKey,
    MessageTooLong,
    RemoteException,
    UnknownError,
    UnknownTarget,
    UnVerifiedSession,
)
from ..util import gen_subclass

if TYPE_CHECKING:
    from ..event import MiraiEvent


code_exceptions_mapping: dict[int, type[Exception]] = {
    1: InvalidVerifyKey,
    2: AccountNotFound,
    3: InvalidSession,
    4: UnVerifiedSession,
    5: UnknownTarget,
    6: FileNotFoundError,
    10: PermissionError,
    20: AccountMuted,
    30: MessageTooLong,
    400: InvalidArgument,
    500: RemoteException,
}


@overload
def validate_response(data: Any, raising: Literal[False]) -> Any | Exception:
    ...


@overload
def validate_response(data: Any, raising: Literal[True] = True) -> Any:
    ...


def validate_response(data: Any, raising: bool = True):
    int_code = data.get("code") if isinstance(data, dict) else data
    if not isinstance(int_code, int) or int_code == 200 or int_code == 0:
        return data.get("data", data)
    exc_cls = code_exceptions_mapping.get(int_code)
    exc = exc_cls(exc_cls.__doc__, data) if exc_cls else UnknownError(data)
    if raising:
        raise exc
    return exc


@lru_cache(maxsize=1024)
def extract_event_type(event_type: str) -> type[MiraiEvent] | None:
    from ..event import MiraiEvent

    return next((cls for cls in gen_subclass(MiraiEvent) if cls.__name__ == event_type), None)


def build_event(data: dict) -> MiraiEvent:
    """
    从尚未明确指定事件类型的对象中获取事件的定义, 并进行解析

    Args:
        data (dict): 用 dict 表示的序列化态事件, 应包含有字段 `type` 以供分析事件定义.

    Raises:
        InvalidArgument: 目标对象中不包含字段 `type`
        ValueError: 没有找到对应的字段, 通常的, 这意味着应用获取到了一个尚未被定义的事件, 请报告问题.

    Returns:
        MiraiEvent: 已经被序列化的事件
    """
    event_type: str | None = data.get("type")
    if not event_type or not isinstance(event_type, str):
        raise InvalidArgument("Unable to find 'type' field for automatic parsing", data)
    event_class: type[MiraiEvent] | None = extract_event_type(event_type)
    if not event_class:
        logger.error("An event is not recognized! Please report with your log to help us diagnose.")
        raise ValueError(f"Unable to find event: {event_type}", data)
    data = {k: v for k, v in data.items() if k != "type"}
    return event_class.parse_obj(data)


class CallMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    RESTGET = "get"
    RESTPOST = "update"
    MULTIPART = "multipart"


class UploadMethod(str, Enum):
    """用于向 `upload` 系列方法描述上传类型"""

    Friend = "friend"
    """好友"""

    Group = "group"
    """群组"""

    Temp = "temp"
    """临时消息"""

    def __str__(self) -> str:
        return self.value


class DatetimeJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return int(obj.timestamp())
        return json.JSONEncoder.default(self, obj)
