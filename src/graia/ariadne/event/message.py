"""Ariadne 消息事件"""
from typing import TYPE_CHECKING, Union

from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from pydantic import Field

from ..dispatcher import (
    BaseDispatcher,
    MessageChainDispatcher,
    SenderDispatcher,
    SourceDispatcher,
    SubjectDispatcher,
)
from ..message.chain import MessageChain
from ..message.element import Source
from ..model import Client, Friend, Group, Member, Stranger
from ..typing import generic_issubclass
from . import MiraiEvent
from .mirai import FriendEvent, GroupEvent


class MessageEvent(MiraiEvent):
    """Ariadne 消息事件基类"""

    type: str = "MessageEvent"

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    sender: Union[Friend, Member, Client, Stranger]
    """发送者"""

    def __int__(self):
        return self.id

    @property
    def id(self) -> int:
        return self.message_chain.get_first(Source).id

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, SourceDispatcher, SenderDispatcher]


class FriendMessage(MessageEvent, FriendEvent):
    """好友消息"""

    type: str = "FriendMessage"

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    sender: Friend
    """发送者"""


class GroupMessage(MessageEvent, GroupEvent):
    """群组消息"""

    type: str = "GroupMessage"

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    sender: Member
    """发送者"""

    class Dispatcher(MessageEvent.Dispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if generic_issubclass(Group, interface.annotation):
                return interface.event.sender.group


class TempMessage(MessageEvent):
    """临时消息"""

    type: str = "TempMessage"

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    sender: Member
    """发送者"""

    class Dispatcher(MessageEvent.Dispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if generic_issubclass(Group, interface.annotation):
                return interface.event.sender.group


class OtherClientMessage(MessageEvent):
    """其他客户端消息"""

    type: str = "OtherClientMessage"

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    sender: Client
    """发送者"""


class StrangerMessage(MessageEvent):
    """陌生人消息"""

    type: str = "StrangerMessage"

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    sender: Stranger
    """发送者"""


class ActiveMessage(MiraiEvent):
    """主动消息: Bot 账号发送给他人的消息"""

    type: str

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    subject: Union[Friend, Group, Member, Stranger]
    """消息接收者"""

    sync: bool = False
    """是否为同步消息"""

    def __int__(self):
        return self.id

    @property
    def id(self) -> int:
        return self.message_chain.get_first(Source).id

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, SourceDispatcher, SubjectDispatcher]

    if not TYPE_CHECKING:

        @property
        def messageId(self) -> int:
            from traceback import format_exception_only
            from warnings import warn

            from loguru import logger

            warning = DeprecationWarning(
                "ActiveMessage.messageId is deprecated since Ariadne 0.9, "
                "and scheduled for removal in in Ariadne 0.10. "
                "Use ActiveMessage.id or int(ActiveMessage) instead."
            )
            warn(warning, stacklevel=2)
            logger.opt(depth=1).warning("".join(format_exception_only(type(warning), warning)).strip())

            return self.id

        @property
        def origin(self) -> MessageChain:
            from traceback import format_exception_only
            from warnings import warn

            from loguru import logger

            warning = DeprecationWarning(
                "ActiveMessage.origin is deprecated since Ariadne 0.9, "
                "and scheduled for removal in in Ariadne 0.10. "
                "Use ActiveMessage.message_chain instead.",
            )
            warn(warning, stacklevel=2)
            logger.opt(depth=2).warning("".join(format_exception_only(type(warning), warning)).strip())

            return self.message_chain


class ActiveFriendMessage(ActiveMessage):
    """主动好友消息"""

    type: str = "ActiveFriendMessage"

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    subject: Friend
    """消息接收者"""


class ActiveGroupMessage(ActiveMessage):
    """主动群组消息"""

    type: str = "ActiveGroupMessage"

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    subject: Group
    """消息接收者"""


class ActiveTempMessage(ActiveMessage):
    """主动临时消息"""

    type: str = "ActiveTempMessage"

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    subject: Member
    """消息接收者"""

    class Dispatcher(ActiveMessage.Dispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if interface.annotation is Group:
                return interface.event.subject.group


class ActiveStrangerMessage(ActiveMessage):
    """主动陌生人消息"""

    type: str = "ActiveStrangerMessage"

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    subject: Stranger
    """消息接收者"""


class SyncMessage(MiraiEvent):
    """同步消息: 从其他客户端同步的主动消息"""

    sync = True


class FriendSyncMessage(SyncMessage, ActiveFriendMessage):
    """好友同步消息"""

    type: str = "FriendSyncMessage"


class GroupSyncMessage(SyncMessage, ActiveGroupMessage):
    """群组同步消息"""

    type: str = "GroupSyncMessage"


class TempSyncMessage(SyncMessage, ActiveTempMessage):
    """临时会话同步消息"""

    type: str = "TempSyncMessage"


class StrangerSyncMessage(SyncMessage, ActiveStrangerMessage):
    """陌生人同步消息"""

    type: str = "StrangerSyncMessage"
