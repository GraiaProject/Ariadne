from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass(init=True, eq=True, repr=True)
class ParamPattern:
    longs: List[str]
    short: Optional[str] = None
    default: Any = None
    help_message: Optional[str] = None


@dataclass(init=True, eq=True, repr=True)
class SwitchParameter(ParamPattern):
    default: bool = False
    auto_reverse: bool = False


@dataclass(init=True, eq=True, repr=True)
class BoxParameter(ParamPattern):
    "可以被指定传入消息的参数, 但只有一个."
