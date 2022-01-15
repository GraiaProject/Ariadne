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


class SendMessageAction(Generic[T, R]):
    """表示 SendMessage 的 action"""

    @staticmethod
    async def param(item: SendMessageDict, /) -> SendMessageDict:
        """传入 SendMessageDict 作为参数, 传出 SendMessageDict 作为结果

        Args:
            item (SendMessageDict): 调用参数

        Returns:
            SendMessageDict: 修改后的调用参数
        """
        return item

    @staticmethod
    async def result(item: "BotMessage", /) -> R:
        """处理返回结果

        Args:
            item (BotMessage): SendMessage 成功时的结果

        Returns:
            R: 要实际由 SendMessage 返回的数据
        """
        return item

    @staticmethod
    async def exception(item: SendMessageException, /) -> T:
        """发生异常时进行处理，可以选择不返回而是直接引发异常

        Args:
            item (SendMessageException): 发生的异常

        Returns:
            T: 将作为 sendMessage 的返回值
        """
        raise item
