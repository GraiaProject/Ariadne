"""Ariadne 的类型标注"""

import builtins
import contextlib
import enum
import sys
import typing
from types import MethodType, TracebackType
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    Callable,
    Dict,
    Generic,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypedDict,
    TypeVar,
    Union,
)

from typing_extensions import Annotated, ParamSpec, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .message.chain import MessageChain
    from .model import BotMessage, Friend, Group, Member

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)

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
    async def param(item: SendMessageDict) -> SendMessageDict:
        """传入 SendMessageDict 作为参数, 传出 SendMessageDict 作为结果

        Args:
            item (SendMessageDict): 调用参数

        Returns:
            SendMessageDict: 修改后的调用参数
        """
        return item

    @staticmethod
    async def result(item: "BotMessage") -> R:
        """处理返回结果

        Args:
            item (BotMessage): SendMessage 成功时的结果

        Returns:
            R: 要实际由 SendMessage 返回的数据
        """
        return item  # type: ignore

    @staticmethod
    async def exception(item: SendMessageException) -> Optional[T]:
        """发生异常时进行处理，可以选择不返回而是直接引发异常

        Args:
            item (SendMessageException): 发生的异常

        Returns:
            T: 将作为 sendMessage 的返回值
        """
        raise item


@runtime_checkable
class SendMessageActionProtocol(Protocol, Generic[T_co]):
    async def param(self, item: SendMessageDict) -> SendMessageDict:
        ...

    async def result(self, item: "BotMessage") -> T_co:
        ...

    async def exception(self, item: SendMessageException) -> Any:
        ...


def generic_issubclass(cls: type, par: Union[type, Any, Tuple[type, ...]]) -> bool:
    """检查 cls 是否是 args 中的一个子类, 支持泛型, Any, Union

    Args:
        cls (type): 要检查的类
        par (Union[type, Any, Tuple[type, ...]]): 要检查的类的父类

    Returns:
        bool: 是否是父类
    """
    if par is Any:
        return True
    with contextlib.suppress(TypeError):
        if isinstance(par, (type, tuple)):
            return issubclass(cls, par)
        if typing.get_origin(par) is Union:
            return any(generic_issubclass(cls, p) for p in typing.get_args(par))
        if isinstance(par, TypeVar):
            if par.__constraints__:
                return any(generic_issubclass(cls, p) for p in par.__constraints__)
            if par.__bound__:
                return generic_issubclass(cls, par.__bound__)
    return False


def generic_isinstance(obj: Any, par: Union[type, Any, Tuple[type, ...]]) -> bool:
    """检查 obj 是否是 args 中的一个类型, 支持泛型, Any, Union

    Args:
        obj (Any): 要检查的对象
        par (Union[type, Any, Tuple[type, ...]]): 要检查的对象的类型

    Returns:
        bool: 是否是类型
    """
    if par is Any:
        return True
    with contextlib.suppress(TypeError):
        if isinstance(par, (type, tuple)):
            return isinstance(obj, par)
        if typing.get_origin(par) is Union:
            return any(generic_isinstance(obj, p) for p in typing.get_args(par))
        if isinstance(par, TypeVar):
            if par.__constraints__:
                return any(generic_isinstance(obj, p) for p in par.__constraints__)
            if par.__bound__:
                return generic_isinstance(obj, par.__bound__)
    return False


class _SentinelClass(enum.Enum):
    _Sentinel = object()


Sentinel = _SentinelClass._Sentinel

AnnotatedType = type(Annotated[int, lambda x: x > 0])

ExceptionHook = Callable[[Type[BaseException], BaseException, Optional[TracebackType]], Any]

if sys.version_info >= (3, 9):
    classmethod = builtins.classmethod
else:

    class classmethod:
        "Emulate PyClassMethod_Type()"

        def __init__(self, f):
            self.f = f

        def __get__(self, obj, cls=None):
            if cls is None:
                cls = type(obj)
            if hasattr(type(self.f), "__get__"):
                return self.f.__get__(cls, cls)
            return MethodType(self.f, cls)
