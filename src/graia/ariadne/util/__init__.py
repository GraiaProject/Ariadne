"""本模块提供 Ariadne 内部使用的小工具, 以及方便的 `async_exec` 模块.
"""

# Utility Layout
import asyncio
import functools
import sys
import traceback
import warnings
from asyncio.events import AbstractEventLoop
from typing import (
    AsyncIterator,
    Callable,
    ContextManager,
    Coroutine,
    Dict,
    Generator,
    List,
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
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.typing import T_Dispatcher
from loguru import logger

from ..exception import (
    AccountMuted,
    AccountNotFound,
    InvalidArgument,
    InvalidSession,
    InvalidVerifyKey,
    MessageTooLong,
    UnknownError,
    UnknownTarget,
    UnVerifiedSession,
)
from ..typing import P, R, T

# Import layout
from . import async_exec  # noqa: F401
from .async_exec import (  # noqa: F401
    IS_MAIN_PROCESS,
    ParallelExecutor,
    cpu_bound,
    io_bound,
)

code_exceptions_mapping: Dict[int, Type[Exception]] = {
    1: InvalidVerifyKey,
    2: AccountNotFound,
    3: InvalidSession,
    4: UnVerifiedSession,
    5: UnknownTarget,
    6: FileNotFoundError,
    10: PermissionError,
    20: AccountMuted,
    30: MessageTooLong,
    400: InvalidArgument,
}


def validate_response(code: Union[dict, int]):
    origin = code
    if isinstance(code, dict):
        code = code.get("code")
    else:
        code = code
    if not isinstance(code, int) or code == 200 or code == 0:
        return
    exc_cls = code_exceptions_mapping.get(code)
    if exc_cls:
        raise exc_cls(exc_cls.__doc__)
    else:
        raise UnknownError(f"{origin}")


def loguru_excepthook(cls, val, tb, *_, **__):
    logger.opt(exception=(cls, val, tb)).error("Exception:")


def loguru_async_handler(loop: AbstractEventLoop, ctx: dict):
    if "exception" in ctx:
        logger.opt(exception=ctx["exception"]).error("Exception:")
    else:
        logger.error(f"Exception: {ctx}")


def inject_loguru_traceback(loop: AbstractEventLoop = None):
    """使用 loguru 模块替换默认的 traceback.print_exception 与 sys.excepthook"""
    traceback.print_exception = loguru_excepthook
    sys.excepthook = loguru_excepthook
    if loop:
        loop.set_exception_handler(loguru_async_handler)


def inject_bypass_listener(broadcast: Broadcast):
    """注入 BypassListener 以享受子事件解析.

    Args:
        broadcast (Broadcast): 外部事件系统, 提供了 event_class_generator 方法以生成子事件.
    """

    class BypassListener(Listener):
        def __init__(
            self,
            callable: Callable,
            namespace: Namespace,
            listening_events: List[Type[Dispatchable]],
            inline_dispatchers: List[T_Dispatcher] = None,
            decorators: List[Decorator] = None,
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
                inline_dispatchers=inline_dispatchers,
                decorators=decorators,
                priority=priority,
            )

    @broadcast.dispatcher_interface.inject_global_raw
    async def _(interface: DispatcherInterface):
        if isinstance(interface.event, interface.annotation):
            return interface.event
        elif (
            hasattr(interface.annotation, "__origin__")
            and interface.annotation.__origin__ is DispatcherInterface
        ):
            return interface

    import graia.broadcast.entities.listener

    graia.broadcast.entities.listener.Listener = BypassListener  # type: ignore
    graia.broadcast.Listener = BypassListener  # type: ignore
    try:  # Override saya listener
        import graia.saya.builtins.broadcast.schema

        graia.saya.builtins.broadcast.schema.Listener = BypassListener  # type: ignore
    except ImportError:  # Saya not installed, pass.
        pass


class ApplicationMiddlewareDispatcher(BaseDispatcher):
    always = True
    context: ContextManager

    def __init__(self, app) -> None:
        self.app = app

    def beforeExecution(self, interface: "DispatcherInterface"):
        from ..context import enter_context

        self.context = enter_context(self.app, interface.event)
        self.context.__enter__()

    def afterExecution(self, interface: "DispatcherInterface", exception, tb):
        self.context.__exit__(exception.__class__ if exception else None, exception, tb)

    async def catch(self, interface: "DispatcherInterface"):
        from ..app import Ariadne

        if interface.annotation is Ariadne:
            return self.app


def app_ctx_manager(func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    async def wrapper(self, *args: P.args, **kwargs: P.kwargs):
        from ..context import enter_context

        with enter_context(app=self):
            return await func(self, *args, **kwargs)

    return wrapper


def gen_subclass(cls: Type[T]) -> Generator[Type[T], None, None]:
    yield cls
    for sub_cls in cls.__subclasses__():
        yield from gen_subclass(sub_cls)


def wrap_bracket(string: str) -> str:
    return string.replace("[", "\\u005b").replace("]", "\\u005d")


T_Callable = TypeVar("T_Callable", bound=Callable)


async def await_predicate(predicate: Callable[[], bool], interval: float = 0.01) -> None:
    while not predicate():
        await asyncio.sleep(interval)


async def yield_with_timeout(
    getter_coro: Callable[[], Coroutine[None, None, T]],
    predicate: Callable[[], bool],
    await_length: float = 0.2,
) -> AsyncIterator[T]:
    last_tsk = None
    while predicate():
        last_tsk = last_tsk or {asyncio.create_task(getter_coro())}
        done, last_tsk = await asyncio.wait(last_tsk, timeout=await_length)
        if not done:
            continue
        for t in done:
            res = await t
            yield res
    if last_tsk:
        for tsk in last_tsk:
            tsk.cancel()


def deprecated(remove_ver: str) -> Callable[[T_Callable], T_Callable]:
    def out_wrapper(func: T_Callable) -> T_Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(DeprecationWarning(f"{func.__qualname__} will be removed in {remove_ver}!"))
            logger.warning(f"Deprecated function: {func.__qualname__}")
            logger.warning(f"{func.__qualname__} will be removed in {remove_ver}!")
            return func(*args, **kwargs)

        return wrapper

    return out_wrapper


def cast_to(obj, typ: Type[T]) -> T:
    if typ:
        return obj


class Dummy:
    def __init__(self, **kwds):
        for k, v in kwds:
            self.__setattr__(k, v)

    def __getattr__(self, *_, **__):
        return self

    def __call__(self, *_, **__):
        return self


inject_loguru_traceback()
