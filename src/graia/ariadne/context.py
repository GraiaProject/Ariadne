"""本模块创建了 Ariadne 中的上下文变量"""
from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio.events import AbstractEventLoop

    from graia.broadcast import Broadcast
    from graia.broadcast.entities.event import Dispatchable

    from .adapter import Adapter
    from .app import Ariadne
    from .model import UploadMethod

    ariadne_ctx: ContextVar[Ariadne] = ContextVar("ariadne")
    adapter_ctx: ContextVar[Adapter] = ContextVar("adapter")
    event_ctx: ContextVar[Dispatchable] = ContextVar("event")
    event_loop_ctx: ContextVar[AbstractEventLoop] = ContextVar("event_loop")
    broadcast_ctx: ContextVar[Broadcast] = ContextVar("broadcast")
    upload_method_ctx: ContextVar[UploadMethod] = ContextVar("upload_method")
else:  # for not crashing pdoc
    ariadne_ctx = ContextVar("ariadne")
    adapter_ctx = ContextVar("adapter")
    event_ctx = ContextVar("event")
    event_loop_ctx = ContextVar("event_loop")
    broadcast_ctx = ContextVar("broadcast")
    upload_method_ctx = ContextVar("upload_method")


@contextmanager
def enter_message_send_context(method: "UploadMethod"):
    """进入消息发送上下文

    Args:
        method (UploadMethod): 消息上下文的枚举对象
    """
    t = upload_method_ctx.set(method)
    yield
    upload_method_ctx.reset(t)


class EventContext(AbstractContextManager):
    """Ariadne 事件上下文的实现"""

    app: "Ariadne"
    event: "Dispatchable"

    def __init__(self, app: "Ariadne" = None, event: "Dispatchable" = None) -> None:
        self.app = app
        self.event = event
        self.token_app = None
        self.token_event = None
        self.token_loop = None
        self.token_bcc = None
        self.token_adapter = None

    def __enter__(self):
        if self.app:
            self.token_app = ariadne_ctx.set(self.app)
            self.token_loop = event_loop_ctx.set(self.app.broadcast.loop)
            self.token_bcc = broadcast_ctx.set(self.app.broadcast)
            self.token_adapter = adapter_ctx.set(self.app.adapter)
        if self.event:
            self.token_event = event_ctx.set(self.event)

    def __exit__(self, _exc_cls, _exc_val, _tb):
        try:
            if self.token_app:
                ariadne_ctx.reset(self.token_app)
            if self.token_adapter:
                adapter_ctx.reset(self.token_adapter)
            if self.token_event:
                event_ctx.reset(self.token_event)
            if self.token_loop:
                event_loop_ctx.reset(self.token_loop)
            if self.token_bcc:
                broadcast_ctx.reset(self.token_bcc)
        except ValueError:
            pass
