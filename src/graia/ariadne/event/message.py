"""Ariadne 消息事件"""
from typing import Union

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from ..dispatcher import (
    ContextDispatcher,
    MessageChainDispatcher,
    SenderDispatcher,
    SourceDispatcher,
)
from ..message.chain import MessageChain
from ..model import Client, Friend, Group, Member, Stranger
from . import MiraiEvent
from .mirai import FriendEvent, GroupEvent


class MessageEvent(MiraiEvent):
    """Ariadne 消息事件基类"""

    type: str = "MessageEvent"
    messageChain: MessageChain
    """消息链"""

    sender: Union[Friend, Member, Client, Stranger]
    """发送者"""

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher, SenderDispatcher]

        @staticmethod
        async def catch(*_):
            pass


class FriendMessage(MessageEvent, FriendEvent):
    """好友消息"""

    type: str = "FriendMessage"

    messageChain: MessageChain
    """消息链"""

    sender: Friend
    """发送者"""

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher, SenderDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, FriendMessage):
                if interface.annotation is Friend:
                    return interface.event.sender


class GroupMessage(MessageEvent, GroupEvent):
    """群组消息"""

    type: str = "GroupMessage"

    messageChain: MessageChain
    """消息链"""

    sender: Member
    """发送者"""

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher, SenderDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, GroupMessage):
                if interface.annotation is Group:
                    return interface.event.sender.group
                if interface.annotation is Member:
                    return interface.event.sender


class TempMessage(MessageEvent):
    """临时消息"""

    type: str = "TempMessage"

    messageChain: MessageChain
    """消息链"""

    sender: Member
    """发送者"""

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher, SenderDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, TempMessage):
                if interface.annotation is Group:
                    return interface.event.sender.group
                if interface.annotation is Member:
                    return interface.event.sender


class OtherClientMessage(MessageEvent):
    """其他客户端消息"""

    type: str = "OtherClientMessage"

    messageChain: MessageChain
    """消息链"""

    sender: Client
    """发送者"""

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher, SenderDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, OtherClientMessage):
                if interface.annotation is Client:
                    return interface.event.sender


class StrangerMessage(MessageEvent):
    """陌生人消息"""

    type: str = "StrangerMessage"

    messageChain: MessageChain
    """消息链"""

    sender: Stranger
    """发送者"""

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher, SenderDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, StrangerMessage):
                if interface.annotation is Friend:
                    return interface.event.sender


class ActiveMessage(MiraiEvent):
    """主动消息: Bot 账号发送给他人的消息"""

    type: str

    messageChain: MessageChain
    """消息链"""

    subject: Union[Friend, Group, Member, Stranger]
    """消息接收者"""

    sync: bool = False
    """是否为同步消息"""


class ActiveFriendMessage(ActiveMessage):
    """主动好友消息"""

    type: str = "ActiveFriendMessage"

    messageChain: MessageChain
    """消息链"""

    subject: Friend
    """消息接收者"""

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher, SenderDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, ActiveFriendMessage):
                if interface.annotation is Friend:
                    return interface.event.subject


class ActiveGroupMessage(ActiveMessage):
    """主动群组消息"""

    type: str = "ActiveGroupMessage"

    messageChain: MessageChain
    """消息链"""

    subject: Group
    """消息接收者"""

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher, SenderDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, ActiveGroupMessage):
                if interface.annotation is Group:
                    return interface.event.subject


class ActiveTempMessage(ActiveMessage):
    """主动临时消息"""

    type: str = "ActiveTempMessage"

    messageChain: MessageChain
    """消息链"""

    subject: Member
    """消息接收者"""

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher, SenderDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, ActiveTempMessage):
                if interface.annotation is Group:
                    return interface.event.subject.group
                if interface.annotation is Member:
                    return interface.event.subject


class ActiveStrangerMessage(ActiveMessage):
    """主动陌生人消息"""

    type: str = "ActiveStrangerMessage"

    messageChain: MessageChain
    """消息链"""

    subject: Stranger
    """消息接收者"""

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher, SenderDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, ActiveStrangerMessage):
                if interface.annotation is Stranger:
                    return interface.event.subject


class FriendSyncMessage(ActiveFriendMessage):
    """好友同步消息"""

    type: str = "FriendSyncMessage"

    sync = True


class GroupSyncMessage(ActiveGroupMessage):
    """群组同步消息"""

    type: str = "GroupSyncMessage"

    sync = True


class TempSyncMessage(ActiveTempMessage):
    """临时会话同步消息"""

    type: str = "TempSyncMessage"

    sync = True


class StrangerSyncMessage(ActiveStrangerMessage):
    """陌生人同步消息"""

    type: str = "StrangerSyncMessage"

    sync = True
