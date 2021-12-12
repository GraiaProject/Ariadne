from loguru import logger

logger.warning("This module is deprecated and will be removed in 0.5.2!")

from .literature import BoxParameter, ParamPattern, SwitchParameter
from .twilight import (
    ArgumentMatch,
    ElementMatch,
    FullMatch,
    Match,
    RegexMatch,
    UnionMatch,
    WildcardMatch,
)
