import functools
import sys
import traceback
from typing import Callable, ContextManager, Generator, List, Type, TypeVar, Union

from graia.broadcast import Broadcast
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.entities.listener import Listener
from graia.broadcast.entities.namespace import Namespace
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.typing import T_Dispatcher
from loguru import logger
from typing_extensions import ParamSpec

from .context import enter_context

P = ParamSpec("P")
R = TypeVar("R")

from .exception import (
    AccountMuted,
    AccountNotFound,
    InvalidArgument,
    InvalidSession,
    InvalidVerifyKey,
    MessageTooLong,
    UnknownTarget,
    UnVerifyedSession,
)

code_exceptions_mapping = {
    1: InvalidVerifyKey,
    2: AccountNotFound,
    3: InvalidSession,
    4: UnVerifyedSession,
    5: UnknownTarget,
    6: FileNotFoundError,
    10: PermissionError,
    20: AccountMuted,
    30: MessageTooLong,
    400: InvalidArgument,
}


def validate_response(code: Union[dict, int]):
    if isinstance(code, dict):
        code = code.get("code")
        exception_code = code_exceptions_mapping.get(code)
        if exception_code:
            raise exception_code
    elif isinstance(code, int):
        exception_code = code_exceptions_mapping.get(code)
        if exception_code:
            raise exception_code


def loguru_print_exception(cls, val, tb, limit, file, chain):
    logger.opt(exception=(cls, val, tb)).error(f"Caught Exception {val}:")


def loguru_excepthook(cls, val, tb):
    logger.opt(exception=(cls, val, tb)).error(f"Uncaught Exception:")


def inject_loguru_traceback():
    """使用 loguru 模块 替换默认的 traceback.print_exception 与 sys.excepthook"""
    traceback.print_exception = loguru_print_exception
    sys.excepthook = loguru_excepthook


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

    import graia.broadcast.entities.listener

    graia.broadcast.entities.listener.Listener = BypassListener
    graia.broadcast.Listener = BypassListener


class ApplicationMiddlewareDispatcher(BaseDispatcher):
    always = True
    context: ContextManager

    def __init__(self, app) -> None:
        self.app = app

    def beforeExecution(self, interface: "DispatcherInterface"):
        self.context = enter_context(self.app, interface.event)
        self.context.__enter__()

    def afterExecution(self, interface: "DispatcherInterface", exception, tb):
        self.context.__exit__(exception.__class__ if exception else None, exception, tb)

    async def catch(self, interface: "DispatcherInterface"):
        from .app import Ariadne

        if interface.annotation is Ariadne:
            return self.app


def app_ctx_manager(func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    async def wrapper(self, *args: P.args, **kwargs: P.kwargs):
        with enter_context(app=self):
            return await func(self, *args, **kwargs)

    return wrapper


T = TypeVar("T")


def gen_subclass(cls: Type[T]) -> Generator[Type[T], None, None]:
    yield cls
    for sub_cls in cls.__subclasses__():
        yield from gen_subclass(sub_cls)
