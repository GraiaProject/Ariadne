"""本模块创建了 Ariadne 中的上下文变量"""

from contextlib import contextmanager, suppress
from contextvars import ContextVar
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from asyncio.events import AbstractEventLoop

    from graia.broadcast import Broadcast
    from graia.broadcast.entities.event import Dispatchable

    from .app import Ariadne
    from .connection.util import UploadMethod

    ariadne_ctx: ContextVar[Ariadne] = ContextVar("ariadne")
    event_ctx: ContextVar[Dispatchable] = ContextVar("event")
    event_loop_ctx: ContextVar[AbstractEventLoop] = ContextVar("event_loop")
    broadcast_ctx: ContextVar[Broadcast] = ContextVar("broadcast")
    upload_method_ctx: ContextVar[UploadMethod] = ContextVar("upload_method")
else:  # for not crashing pdoc
    ariadne_ctx = ContextVar("ariadne")
    event_ctx = ContextVar("event")
    event_loop_ctx = ContextVar("event_loop")
    broadcast_ctx = ContextVar("broadcast")
    upload_method_ctx = ContextVar("upload_method")

context_map: Dict[str, ContextVar] = {
    "Ariadne": ariadne_ctx,
    "Dispatchable": event_ctx,
    "AbstractEventLoop": event_loop_ctx,
    "Broadcast": broadcast_ctx,
    "UploadMethod": upload_method_ctx,
}


@contextmanager
def enter_message_send_context(method: "UploadMethod"):
    """进入消息发送上下文

    Args:
        method (UploadMethod): 消息上下文的枚举对象
    """
    t = upload_method_ctx.set(method)
    yield
    upload_method_ctx.reset(t)


@contextmanager
def enter_context(app: Optional["Ariadne"] = None, event: Optional["Dispatchable"] = None):
    """进入事件上下文

    Args:
        app (Ariadne, optional): Ariadne 实例.
        event (Dispatchable, optional): 当前事件
    """
    token_loop = None
    token_bcc = None
    token_app = None
    if app:
        token_app = ariadne_ctx.set(app)
        token_loop = event_loop_ctx.set(app.service.loop)
        token_bcc = broadcast_ctx.set(app.service.broadcast)
    token_event = event_ctx.set(event) if event else None
    yield

    with suppress(ValueError):
        if token_app:
            ariadne_ctx.reset(token_app)
        if token_event:
            event_ctx.reset(token_event)
        if token_loop:
            event_loop_ctx.reset(token_loop)
        if token_bcc:
            broadcast_ctx.reset(token_bcc)
