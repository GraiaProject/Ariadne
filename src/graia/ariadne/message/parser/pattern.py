"""消息链处理器的 "模式", 将在 0.5.2 移除"""
from loguru import logger

from .literature import BoxParameter, ParamPattern, SwitchParameter  # noqa: F401
from .twilight import (  # noqa: F401
    ArgumentMatch,
    ElementMatch,
    FullMatch,
    Match,
    RegexMatch,
    UnionMatch,
    WildcardMatch,
)

logger.warning("This module is deprecated and will be removed in 0.5.2!")
