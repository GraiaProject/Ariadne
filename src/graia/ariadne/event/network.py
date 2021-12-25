"""网络相关的事件, 通常为异常发生"""
from graia.broadcast.entities.event import Dispatchable

from ..dispatcher import ContextDispatcher


class RemoteException(Dispatchable):
    """网络异常: 无头客户端处发生错误, 你应该检查其输出的错误日志."""

    Dispatcher = ContextDispatcher


class InvalidRequest(Dispatchable):
    """网络异常: 意料之外地, 发出了不被无头客户端接收的 HTTP 请求, 你应该通过相应渠道向我们汇报此问题"""

    Dispatcher = ContextDispatcher
