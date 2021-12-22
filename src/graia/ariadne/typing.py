"""Ariadne 的类型标注"""
from typing import (
    AbstractSet,
    Any,
    Dict,
    Generic,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from typing_extensions import ParamSpec

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")

Self = TypeVar("Self")

T_start = TypeVar("T_start")
T_stop = TypeVar("T_stop")
T_step = TypeVar("T_step")


class Slice(Generic[T_start, T_stop, T_step]):
    """对 slice 对象的泛型化包装, 但无法直接继承于 slice"""

    start: T_start
    stop: T_stop
    step: T_step


MessageIndex = Tuple[int, Optional[int]]

IntStr = Union[int, str]
AbstractSetIntStr = AbstractSet[IntStr]
DictIntStrAny = Dict[IntStr, Any]
DictStrAny = Dict[str, Any]
MappingIntStrAny = Mapping[IntStr, Any]
ReprArgs = Sequence[Tuple[Optional[str], Any]]
