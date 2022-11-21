"""本模块提供 Ariadne 内部使用的小工具, 以及方便的辅助模块."""


# Utility Layout
import functools
import inspect
import sys
import traceback
import types
import typing
import warnings
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Callable,
    Generator,
    Iterable,
    List,
    MutableSet,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from loguru import logger

from graia.broadcast import Broadcast
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities.listener import Listener
from graia.broadcast.entities.namespace import Namespace
from graia.broadcast.exceptions import ExecutionStop, PropagationCancelled, RequirementCrashed
from graia.broadcast.typing import T_Dispatcher
from graia.broadcast.utilles import dispatcher_mixin_handler

from ..typing import ExceptionHook, P, R, T, Wrapper

if TYPE_CHECKING:
    from datetime import datetime

    from rich.console import Console
    from rich.text import Text


def type_repr(obj) -> str:
    """Return the repr() of an object, special-casing types (internal helper).

    If obj is a type, we return a shorter version than the default
    type.__repr__, based on the module and qualified name, which is
    typically enough to uniquely identify a type.  For everything
    else, we fall back on repr(obj).
    """
    if isinstance(obj, getattr(types, "GenericAlias", type(None))):
        return repr(obj)
    if isinstance(obj, type):
        if obj.__module__ == "builtins":
            return obj.__qualname__
        return f"{obj.__module__}.{obj.__qualname__}"
    if obj is Ellipsis:
        return "..."
    return obj.__name__ if isinstance(obj, types.FunctionType) else repr(obj)


def loguru_exc_callback(cls: Type[BaseException], val: BaseException, tb: Optional[TracebackType], *_, **__):
    """loguru 异常回调

    Args:
        cls (Type[Exception]): 异常类
        val (Exception): 异常的实际值
        tb (TracebackType): 回溯消息
    """
    if not issubclass(cls, (ExecutionStop, PropagationCancelled)):
        logger.opt(exception=(cls, val, tb)).error("Exception:")


def loguru_exc_callback_async(loop, context: dict):
    """loguru 异步异常回调

    Args:
        loop (AbstractEventLoop): 异常发生的事件循环
        context (dict): 异常上下文
    """
    message = context.get("message")
    if not message:
        message = "Unhandled exception in event loop"
    if (
        handle := context.get("handle")
    ) and handle._callback.__qualname__ == "ClientConnectionRider.connection_manage.<locals>.<lambda>":
        logger.warning("Uncompleted aiohttp transport", style="yellow bold")
        return
    exception = context.get("exception")
    if exception is None:
        exc_info = False
    elif isinstance(exception, (ExecutionStop, PropagationCancelled, RequirementCrashed)):
        return
    else:
        exc_info = (type(exception), exception, exception.__traceback__)
    if (
        "source_traceback" not in context
        and loop._current_handle is not None
        and loop._current_handle._source_traceback
    ):
        context["handle_traceback"] = loop._current_handle._source_traceback

    log_lines = [message]
    for key in sorted(context):
        if key in {"message", "exception"}:
            continue
        value = context[key]
        if key == "handle_traceback":
            tb = "".join(traceback.format_list(value))
            value = "Handle created at (most recent call last):\n" + tb.rstrip()
        elif key == "source_traceback":
            tb = "".join(traceback.format_list(value))
            value = "Object created at (most recent call last):\n" + tb.rstrip()
        else:
            value = repr(value)
        log_lines.append(f"{key}: {value}")

    logger.opt(exception=exc_info).error("\n".join(log_lines))


class RichLogInstallOptions(NamedTuple):
    """安装 Rich log 的选项"""

    rich_console: Optional["Console"] = None
    exc_hook: Union[ExceptionHook, None] = loguru_exc_callback
    rich_traceback: bool = False
    tb_ctx_lines: int = 3
    tb_theme: Optional[str] = None
    tb_suppress: Iterable[Union[str, types.ModuleType]] = ()
    time_format: Union[str, Callable[["datetime"], "Text"]] = "[%x %X]"
    keywords: Optional[List[str]] = None
    level: Union[int, str] = 20


def inject_bypass_listener(broadcast: Broadcast):
    """注入 BypassListener 以享受子事件解析.

    Args:
        broadcast (Broadcast): 外部事件系统, 提供了 event_class_generator 方法以生成子事件.
    """

    class BypassListener(Listener):
        """透传监听器的实现"""

        def __init__(
            self,
            callable: Callable,
            namespace: Namespace,
            listening_events: List[Type[Dispatchable]],
            inline_dispatchers: Optional[List[T_Dispatcher]] = None,
            decorators: Optional[List[Decorator]] = None,
            priority: int = 16,
        ) -> None:
            events = []
            for event in listening_events:
                events.append(event)
                events.extend(broadcast.event_class_generator(event))
            super().__init__(
                callable,
                namespace,
                events,
                inline_dispatchers=inline_dispatchers or [],
                decorators=decorators or [],
                priority=priority,
            )

    import creart

    import graia.broadcast.entities.listener

    graia.broadcast.entities.listener.Listener = BypassListener  # type: ignore
    graia.broadcast.Listener = BypassListener  # type: ignore

    if creart.exists_module("graia.saya"):
        import graia.saya.builtins.broadcast.schema

        graia.saya.builtins.broadcast.schema.Listener = BypassListener  # type: ignore


def ariadne_api(func: Callable[P, R]) -> Callable[P, R]:
    """包装声明需要在 Ariadne Context 中执行的函数

    Args:
        func (Callable[P, R]): 被包装的函数

    Returns:
        Callable[P, R]: 包装后的函数
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs):
        from ..context import enter_context

        sys.audit("CallAriadneAPI", func.__name__, args, kwargs)

        with enter_context(app=args[0]):  # type: ignore
            return func(*args, **kwargs)

    return wrapper


def gen_subclass(cls: Type[T]) -> Generator[Type[T], None, None]:
    """生成某个类的所有子类 (包括其自身)

    Args:
        cls (Type[T]): 类

    Yields:
        Type[T]: 子类
    """
    yield cls
    for sub_cls in cls.__subclasses__():
        if TYPE_CHECKING:
            assert issubclass(sub_cls, cls)
        yield from gen_subclass(sub_cls)


def escape_bracket(string: str) -> str:
    """在字符串中转义中括号"""
    return string.replace("[", "\\u005b").replace("]", "\\u005d")


def unescape_bracket(string: str) -> str:
    """在字符串中反转义中括号"""
    return string.replace("\\u005b", "[").replace("\\u005d", "]")


def constant(val: T) -> Callable[[], T]:
    """生成一个返回常量的 Callable

    Args:
        val (T): 常量

    Returns:
        Callable[[], T]: 返回的函数
    """
    return lambda: val


def deprecated(remove_ver: str, suggestion: Optional[str] = None) -> Wrapper:
    """标注一个方法 / 函数已被弃用

    Args:
        remove_ver (str): 将被移除的版本.
        suggestion (Optional[str], optional): 建议的替代方案. Defaults to None.

    Returns:
        Callable[[T_Callable], T_Callable]: 包装器.
    """
    __warning_info: MutableSet[Tuple[str, int]] = set()

    def out_wrapper(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            frame = inspect.stack()[1].frame
            caller_file = frame.f_code.co_filename
            caller_line = frame.f_lineno
            if (caller_file, caller_line) not in __warning_info:
                __warning_info.add((caller_file, caller_line))
                warnings.warn(DeprecationWarning(f"{func.__qualname__} will be removed in {remove_ver}!"))
                logger.warning(f"Deprecated function: {func.__qualname__}")
                logger.warning(f"{func.__qualname__} will be removed in {remove_ver}!")
                if suggestion:
                    logger.warning(f"{suggestion}", style="dark_orange bold")
            return func(*args, **kwargs)

        return wrapper

    return out_wrapper


def resolve_dispatchers_mixin(dispatchers: Iterable[T_Dispatcher]) -> List[T_Dispatcher]:
    """解析 dispatcher list 的 mixin

    Args:
        dispatchers (Iterable[T_Dispatcher]): dispatcher 列表

    Returns:
        List[T_Dispatcher]: 解析后的 dispatcher 列表
    """
    result = []
    for dispatcher in dispatchers:
        result.extend(dispatcher_mixin_handler(dispatcher))
    return result


class Dummy:
    """Dummy 类, 对所有调用返回 None. (可以预设某些值)"""

    def __init__(self, **kwds):
        for k, v in kwds.items():
            self.__setattr__(k, v)

    def __getattr__(self, *_, **__):
        return self

    def __call__(self, *_, **__):
        return self

    def __await__(self):
        yield
        return self


def get_cls(obj) -> Optional[type]:
    """获取一个对象的类型，支持 GenericAlias"""
    if cls := typing.get_origin(obj):
        return cls
    if isinstance(obj, type):
        return obj


_T_cls = TypeVar("_T_cls", bound=type)

__SAFE_MODULES__: List[str] = ["graia", "launart", "statv", "pydantic", "aiohttp", "avilla"]


def internal_cls(alt: Optional[Callable] = None) -> Callable[[_T_cls], _T_cls]:
    """将一个类型包装为内部类, 可通过 __SAFE_MODULES__ 定制."""
    if alt:
        hint = f"Use {alt.__module__}.{alt.__qualname__}!"
    else:
        hint = "Only modules start with {module} can initialize it!"

    SAFE_MODULES = tuple(__SAFE_MODULES__)

    def deco(cls: _T_cls) -> _T_cls:
        origin_init = cls.__init__

        @functools.wraps(origin_init)
        def _wrapped_init_(self: object, *args, **kwargs):
            frame = inspect.stack()[1].frame  # outer frame
            module_name: str = frame.f_globals["__name__"]
            if not module_name.startswith(SAFE_MODULES):
                raise NameError(
                    f"{self.__class__.__module__}.{self.__class__.__qualname__} is an internal class!",
                    hint.format(module=self.__class__.__module__),
                )
            return origin_init(self, *args, **kwargs)

        cls.__init__ = _wrapped_init_
        return cls

    return deco


def camel_to_snake(name: str) -> str:
    """将 camelCase 字符串转换为 snake_case 字符串"""
    if "_" in name:
        return name
    import re

    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    name = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name)
    name = name.replace("-", "_").lower()
    return name


def snake_to_camel(name: str, capital: bool = False) -> str:
    """将 snake_case 字符串转换为 camelCase 字符串"""
    name = "".join(seg.capitalize() for seg in name.split("_"))
    if not capital:
        name = name[0].lower() + name[1:]
    return name
