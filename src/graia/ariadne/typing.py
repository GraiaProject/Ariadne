from typing import Generic, Optional, Tuple, TypeVar

from typing_extensions import ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

Self = TypeVar("Self")

T_start = TypeVar("T_start")
T_stop = TypeVar("T_stop")
T_step = TypeVar("T_step")


class Slice(Generic[T_start, T_stop, T_step]):
    start: T_start
    stop: T_stop
    step: T_step


MessageIndex = Tuple[int, Optional[int]]
