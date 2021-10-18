from datetime import datetime
from typing import List, Union

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from graia.ariadne.dispatcher import (
    ApplicationDispatcher,
    MessageChainDispatcher,
    SourceDispatcher,
)
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.model import Client, Friend, Group, Member

from . import MiraiEvent


class MessageEvent(MiraiEvent):
    type: str = "MessageEvent"
    messageChain: MessageChain
    sender: Union[Friend, Member, Client]

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ApplicationDispatcher, SourceDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface):
            pass


class FriendMessage(MessageEvent):
    type: str = "FriendMessage"
    messageChain: MessageChain
    sender: Friend

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ApplicationDispatcher, SourceDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["FriendMessage"]):
            if interface.annotation is Friend:
                return interface.event.sender


class GroupMessage(MessageEvent):
    type: str = "GroupMessage"
    messageChain: MessageChain
    sender: Member

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ApplicationDispatcher, SourceDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["GroupMessage"]):
            if interface.annotation is Group:
                return interface.event.sender.group
            elif interface.annotation is Member:
                return interface.event.sender


class TempMessage(MessageEvent):
    type: str = "TempMessage"
    messageChain: MessageChain
    sender: Member

    @classmethod
    def parse_obj(cls, obj):
        return super().parse_obj(obj)

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ApplicationDispatcher, SourceDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["TempMessage"]):
            if interface.annotation is Group:
                return interface.event.sender.group
            elif interface.annotation is Member:
                return interface.event.sender


class OtherClientMessage(MessageEvent):
    type: str = "OtherClientMessage"
    messageChain: MessageChain
    sender: Client

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ApplicationDispatcher, SourceDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["OtherClientMessage"]):
            if interface.annotation is Client:
                return interface.event.sender


class StrangerMessage(MessageEvent):
    type: str = "StrangerMessage"
    messageChain: MessageChain
    sender: Friend  # use Friend because it has the same structure as the stranger.

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, ApplicationDispatcher, SourceDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["StrangerMessage"]):
            if interface.annotation is Friend:
                return interface.event.sender
