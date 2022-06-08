"""本模块提供 Ariadne 内部使用的小工具, 以及方便的 `async_exec` 模块.
"""

import contextlib

# Utility Layout
import functools
import inspect
import sys
import types
import typing
import warnings
from contextvars import ContextVar
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
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

from graia.broadcast import Broadcast
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities.listener import Listener
from graia.broadcast.entities.namespace import Namespace
from graia.broadcast.exceptions import (
    ExecutionStop,
    PropagationCancelled,
    RequirementCrashed,
)
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.typing import T_Dispatcher
from graia.broadcast.utilles import dispatcher_mixin_handler
from loguru import logger

from ..typing import DictStrAny, ExceptionHook, P, R, T

if TYPE_CHECKING:
    from datetime import datetime

    from rich.console import Console
    from rich.text import Text


def loguru_exc_callback(cls: Type[BaseException], val: BaseException, tb: Optional[TracebackType], *_, **__):
    """loguru 异常回调

    Args:
        cls (Type[Exception]): 异常类
        val (Exception): 异常的实际值
        tb (TracebackType): 回溯消息
    """
    if issubclass(cls, (ExecutionStop, PropagationCancelled)):
        return
    if tb:
        exec_module_name = tb.tb_frame.f_globals.get("__name__", "")
        if isinstance(val, RequirementCrashed) and exec_module_name.startswith("graia.broadcast"):
            with contextlib.suppress(Exception):
                local_dict = tb.tb_frame.f_locals
                _, param_name, param_anno, param_default = val.args
                if isinstance(param_anno, type):
                    param_anno = param_anno.__qualname__
                param_repr = "".join(
                    [
                        param_name,
                        f": {param_anno}" if param_anno else "",
                        f" = {param_default}" if param_default else "",
                    ]
                )
                val = RequirementCrashed(
                    f"Unable to lookup parameter ({param_repr})",
                    local_dict["dispatchers"],
                )

    logger.opt(exception=(cls, val, tb)).error("Exception:")


def loguru_exc_callback_async(_, ctx: dict):
    """loguru 异步异常回调

    Args:
        _ (AbstractEventLoop): 异常发生的事件循环
        ctx (dict): 异常上下文
    """
    if "exception" in ctx:
        if isinstance(ctx["exception"], (ExecutionStop, PropagationCancelled, RequirementCrashed)):
            return
        logger.opt(exception=ctx["exception"]).error("Exception:")
    else:
        logger.error(f"Exception: {ctx}")


class RichLogInstallOptions(NamedTuple):
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

    import graia.broadcast.entities.listener

    graia.broadcast.entities.listener.Listener = BypassListener  # type: ignore
    graia.broadcast.Listener = BypassListener  # type: ignore
    try:  # Override saya listener
        import graia.saya.builtins.broadcast.schema

        graia.saya.builtins.broadcast.schema.Listener = BypassListener  # type: ignore
    except ImportError:  # Saya not installed, pass.
        pass


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
    """在字符串中转义中括号括号"""
    return string.replace("[", "\\u005b").replace("]", "\\u005d")


def constant(val: T) -> Callable[[], T]:
    """生成一个返回常量的 Callable

    Args:
        val (T): 常量

    Returns:
        Callable[[], T]: 返回的函数
    """
    return lambda: val


def get_stack_namespace(
    layer: int = 0, globals_: Optional[DictStrAny] = None, locals_: Optional[DictStrAny] = None
) -> Tuple[DictStrAny, DictStrAny]:
    """获取一个上下文的全局和局部变量

    Args:
        layer (int, optional): 层数. Defaults to 0.
        globals_ (Optional[DictStrAny], optional): 全局变量. Defaults to None.
        locals_ (Optional[DictStrAny], optional): 局部变量. Defaults to None.

    Returns:
        Tuple[DictStrAny, DictStrAny]: 全局和局部变量字典.
    """
    frame = inspect.stack()[layer + 1].frame  # add the current frame
    global_dict, local_dict = frame.f_globals, frame.f_locals
    global_dict.update(globals_ or {})
    local_dict.update(locals_ or {})
    return global_dict, local_dict


T_Callable = TypeVar("T_Callable", bound=Callable)


def deprecated(
    remove_ver: str, suggestion: Optional[str] = None
) -> Callable[[Callable[P, R]], Callable[P, R]]:
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


class ConstantDispatcher(BaseDispatcher):
    """分发常量给指定名称的参数"""

    def __init__(self, context: ContextVar[Dict[str, Any]]) -> None:
        self.ctx_var = context

    async def catch(self, interface: DispatcherInterface):
        if interface.name in self.ctx_var.get():
            return self.ctx_var.get()[interface.name]


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
    if cls := typing.get_origin(obj):
        return cls
    if isinstance(obj, type):
        return obj


_T_cls = TypeVar("_T_cls", bound=type)


def internal_cls(module: str = "graia", alt: Optional[Callable] = None) -> Callable[[_T_cls], _T_cls]:
    if alt:
        hint = f"Use {alt.__module__}.{alt.__qualname__}!"
    else:
        hint = f"Only modules start with {module} can initialize it!"

    def deco(cls: _T_cls) -> _T_cls:
        origin_init = cls.__init__

        @functools.wraps(origin_init)
        def _wrapped_init_(self: object, *args, **kwargs):
            frame = inspect.stack()[1].frame  # outer frame
            module_name: str = frame.f_globals["__name__"]
            if not module_name.startswith(module):
                raise NameError(
                    f"{self.__class__.__module__}.{self.__class__.__qualname__} is an internal class!",
                    hint,
                )
            return origin_init(self, *args, **kwargs)

        cls.__init__ = _wrapped_init_
        return cls

    return deco


def camel_to_snake(name: str) -> str:
    if "_" in name:
        return name
    import re

    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    name = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name)
    name = name.replace("-", "_").lower()
    return name


def snake_to_camel(name: str, capital: bool = False) -> str:
    name = "".join(seg.capitalize() for seg in name.split("_"))
    if not capital:
        name = name[0].lower() + name[1:]
    return name


class AttrConvertMixin:
    __warning_info: ClassVar[Dict[type, MutableSet[Tuple[str, int]]]] = {}

    if not TYPE_CHECKING:  # Runtime Only

        def __getattr__(self, name: str) -> Any:
            # camelCase to snake_case
            name = camel_to_snake(name)
            if name not in self.__class__.__dict__:
                raise AttributeError(f"'{self.__class__.__qualname__}' object has no attribute '{name}'")
            # extract caller's file and line number
            frame = inspect.stack()[1].frame
            caller_file = frame.f_code.co_filename
            caller_line = frame.f_lineno
            AttrConvertMixin.__warning_info.setdefault(self.__class__, set())
            if (caller_file, caller_line) not in AttrConvertMixin.__warning_info[self.__class__]:
                AttrConvertMixin.__warning_info[self.__class__].add((caller_file, caller_line))
                logger.warning(f"At {caller_file}:{caller_line}")
                logger.warning(f"Found deprecated call: {self.__class__.__qualname__}.{name}!")
            return getattr(self, name)
