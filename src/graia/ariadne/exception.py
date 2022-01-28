"""Ariadne 的异常定义"""


class InvalidEventTypeDefinition(Exception):
    """不合法的事件类型定义."""


class InvalidVerifyKey(Exception):
    """无效的 verifyKey 或其配置."""


class AccountNotFound(Exception):
    """未能使用所配置的账号激活 sessionKey, 请检查 mirai_session 配置."""


class InvalidSession(Exception):
    """无效的 sessionKey, 请重新获取."""


class UnVerifiedSession(Exception):
    """尚未验证/绑定的 session."""


class UnknownTarget(Exception):
    """对象位置未知, 不存在或不可及."""


class AccountMuted(Exception):
    """账号在对象所在聊天区域被封禁."""


class MessageTooLong(Exception):
    """消息过长, 尝试分段发送或报告问题."""


class InvalidArgument(Exception):
    """操作参数不合法, 请报告问题."""


class NotSupportedAction(Exception):
    """该版本不支持本接口."""


class DeprecatedImpl(Exception):
    """该接口已弃用."""


class MissingNecessaryArgument(Exception):
    """应在所提到的参数之中至少传入/使用一个"""


class ConflictItem(Exception):
    """项冲突/其中一项被重复定义"""


class RemoteException(Exception):
    """网络异常: 无头客户端处发生错误, 你应该检查其输出的错误日志."""


class UnknownError(Exception):
    """其他错误"""
