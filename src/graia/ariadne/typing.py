"""Ariadne 的类型标注"""
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    Dict,
    Generic,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
    overload,
)

from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from .message.chain import MessageChain
    from .model import BotMessage, Friend, Group, Member

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")

T_start = TypeVar("T_start")
T_stop = TypeVar("T_stop")
T_step = TypeVar("T_step")


class Slice(Generic[T_start, T_stop, T_step]):  # type: ignore
    """对 slice 对象的泛型化包装, 但无法直接继承于 slice"""

    start: T_start
    stop: T_stop
    step: T_step


MessageIndex = Union[Tuple[int, Optional[int]], int]

IntStr = Union[int, str]
AbstractSetIntStr = AbstractSet[IntStr]
DictIntStrAny = Dict[IntStr, Any]
DictStrAny = Dict[str, Any]
MappingIntStrAny = Mapping[IntStr, Any]
ReprArgs = Sequence[Tuple[Optional[str], Any]]


class SendMessageDict(TypedDict):
    """使用 SendMessage 时, 对 action 传入的字典"""

    message: "MessageChain"
    target: "Union[Group, Friend, Member]"
    quote: Optional[int]


if TYPE_CHECKING:

    class SendMessageException(Exception):
        """携带了 SendMessageDict 的 Exception"""

        send_data: SendMessageDict

else:
    SendMessageException = Exception


class SendMessageAction(Generic[T]):
    """表示 SendMessage 的 action"""

    @overload
    async def __call__(self, item: SendMessageDict) -> SendMessageDict:
        ...

    @overload
    async def __call__(self, item: Union["BotMessage", SendMessageException]) -> T:
        ...
