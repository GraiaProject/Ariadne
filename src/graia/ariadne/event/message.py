"""Ariadne 消息事件"""
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, root_validator

from graia.amnesia.message import Element
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from ..dispatcher import (
    BaseDispatcher,
    MessageChainDispatcher,
    QuoteDispatcher,
    SenderDispatcher,
    SourceDispatcher,
    SubjectDispatcher,
)
from ..message.chain import MessageChain
from ..message.element import Quote, Source
from ..model import Client, Friend, Group, Member, Stranger
from ..typing import generic_issubclass
from . import MiraiEvent
from .mirai import FriendEvent, GroupEvent


def _set_source_quote(_, values: Dict[str, Any]) -> Dict[str, Any]:
    chain: List[Union[Dict[str, Any], Element]] = values["messageChain"]
    for element in chain[:2]:
        if isinstance(element, dict):
            elem_typ: str = element.get("type", "Unknown")
        elif isinstance(element, Element):
            elem_typ: str = element.__class__.__name__
        else:
            continue
        if elem_typ == "Source":
            values["source"] = element
        elif elem_typ == "Quote":
            values["quote"] = element
    values["messageChain"] = list(
        filter(
            lambda x: (x.get("type", "Unknown") if isinstance(x, dict) else x.__class__.__name__)
            not in ("Source", "Quote"),
            chain,
        )
    )
    return values


class MessageEvent(MiraiEvent):
    """Ariadne 消息事件基类"""

    type: str = "MessageEvent"

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    sender: Union[Friend, Member, Client, Stranger]
    """发送者"""

    source: Source
    """消息元数据标识"""

    quote: Optional[Quote] = None
    """可能的引用消息对象"""

    __source_quote_setter = root_validator(pre=True, allow_reuse=True)(_set_source_quote)

    def __int__(self):
        return self.id

    @property
    def id(self) -> int:
        return self.source.id

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, SourceDispatcher, QuoteDispatcher, SenderDispatcher]


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
            if isinstance(interface.event, GroupMessage) and generic_issubclass(Group, interface.annotation):
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
            if isinstance(interface.event, TempMessage) and generic_issubclass(Group, interface.annotation):
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
    """主动消息：Bot 账号发送给他人的消息"""

    type: str

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    subject: Union[Friend, Group, Member, Stranger]
    """消息接收者"""

    sync: bool = False
    """是否为同步消息"""

    source: Source
    """消息元数据标识"""

    quote: Optional[Quote] = None
    """可能的引用消息对象"""

    __source_quote_setter = root_validator(pre=True, allow_reuse=True)(_set_source_quote)

    def __int__(self):
        return self.id

    @property
    def id(self) -> int:
        return self.source.id

    class Dispatcher(BaseDispatcher):
        mixin = [MessageChainDispatcher, SourceDispatcher, QuoteDispatcher, SubjectDispatcher]


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
            if isinstance(interface.event, ActiveTempMessage) and interface.annotation is Group:
                return interface.event.subject.group


class ActiveStrangerMessage(ActiveMessage):
    """主动陌生人消息"""

    type: str = "ActiveStrangerMessage"

    message_chain: MessageChain = Field(..., alias="messageChain")
    """消息链"""

    subject: Stranger
    """消息接收者"""


class SyncMessage(MiraiEvent):
    """同步消息：从其他客户端同步的主动消息"""

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
