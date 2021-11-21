from typing import TYPE_CHECKING, Generic, Tuple, TypeVar

if TYPE_CHECKING:
    Self = TypeVar("Self")

    T_start = TypeVar("T_start")
    T_stop = TypeVar("T_stop")
    T_step = TypeVar("T_step")

    class Slice(slice, Generic[T_start, T_stop, T_step]):
        start: T_start
        stop: T_stop
        step: T_step

    MessageIndex = Tuple[int, int]
