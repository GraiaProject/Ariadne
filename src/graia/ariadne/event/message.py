"""Ariadne 消息事件"""
from typing import Union

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from ..dispatcher import ContextDispatcher, MessageChainDispatcher, SourceDispatcher
from ..message.chain import MessageChain
from ..model import Client, Friend, Group, Member, Stranger
from . import MiraiEvent
from .mirai import FriendEvent, GroupEvent


class MessageEvent(MiraiEvent):
    """Ariadne 消息事件基类"""

    type: str = "MessageEvent"
    messageChain: MessageChain
    sender: Union[Friend, Member, Client, Stranger]

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface):
            pass


class FriendMessage(MessageEvent, FriendEvent):
    """好友消息"""

    type: str = "FriendMessage"
    messageChain: MessageChain
    sender: Friend

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["FriendMessage"]):
            if interface.annotation is Friend:
                return interface.event.sender


class GroupMessage(MessageEvent, GroupEvent):
    """群组消息"""

    type: str = "GroupMessage"
    messageChain: MessageChain
    sender: Member

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["GroupMessage"]):
            if interface.annotation is Group:
                return interface.event.sender.group
            if interface.annotation is Member:
                return interface.event.sender


class TempMessage(MessageEvent):
    """临时消息"""

    type: str = "TempMessage"
    messageChain: MessageChain
    sender: Member

    class Dispatcher(BaseDispatcher):  # pylint: disable-next=missing-class-docstring

        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["TempMessage"]):
            if interface.annotation is Group:
                return interface.event.sender.group
            if interface.annotation is Member:
                return interface.event.sender


class OtherClientMessage(MessageEvent):
    """其他客户端消息"""

    type: str = "OtherClientMessage"
    messageChain: MessageChain
    sender: Client

    class Dispatcher(BaseDispatcher):  # pylint: disable-next=missing-class-docstring

        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["OtherClientMessage"]):
            if interface.annotation is Client:
                return interface.event.sender


class StrangerMessage(MessageEvent):
    """陌生人消息"""

    type: str = "StrangerMessage"
    messageChain: MessageChain
    sender: Stranger

    class Dispatcher(BaseDispatcher):  # pylint: disable-next=missing-class-docstring

        mixin = [MessageChainDispatcher, ContextDispatcher, SourceDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["StrangerMessage"]):
            if interface.annotation is Friend:
                return interface.event.sender
