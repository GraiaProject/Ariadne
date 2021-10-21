import functools
from typing import Callable, ContextManager, TypeVar, Union

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
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
