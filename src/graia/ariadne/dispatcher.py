"""Ariadne 内置的 Dispatcher"""

import asyncio
import contextlib

from launart import ExportInterface, Launart

from graia.broadcast import Broadcast
from graia.broadcast.entities.dispatcher import BaseDispatcher as AbstractDispatcher
from graia.broadcast.entities.signatures import Force
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from .message.chain import MessageChain
from .message.element import Quote, Source
from .model.relationship import Friend, Group, Member
from .typing import generic_isinstance, generic_issubclass


class MessageChainDispatcher(AbstractDispatcher):
    """从 MessageEvent 提取 MessageChain 的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        from .event.message import ActiveMessage, MessageEvent

        if isinstance(interface.event, (MessageEvent, ActiveMessage)) and generic_issubclass(
            MessageChain, interface.annotation
        ):
            return interface.event.message_chain


class ContextDispatcher(AbstractDispatcher):
    """提取上下文的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        from .app import Ariadne

        if generic_isinstance(interface.event, interface.annotation):
            return interface.event

        if generic_issubclass(Broadcast, interface.annotation):
            return Ariadne.service.broadcast

        if generic_issubclass(asyncio.AbstractEventLoop, interface.annotation):
            return Ariadne.service.broadcast.loop

        if generic_issubclass(Ariadne, interface.annotation):
            return Ariadne.current()


class LaunartInterfaceDispatcher(AbstractDispatcher):
    @staticmethod
    async def catch(interface: DispatcherInterface):
        from graia.ariadne.typing import Unions, get_args, get_origin

        if isinstance(interface.annotation, type) and issubclass(interface.annotation, ExportInterface):
            manager = Launart.current()
            with contextlib.suppress(ValueError):
                return manager.get_interface(interface.annotation)
        elif get_origin(interface.annotation) in Unions and (types := get_args(interface.annotation)):
            manager = Launart.current()
            for anno in types:
                if isinstance(anno, type) and issubclass(anno, ExportInterface):
                    with contextlib.suppress(ValueError):
                        return manager.get_interface(anno)


class NoneDispatcher(AbstractDispatcher):
    """给 Optional[...] 提供 None 的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        if NoneDispatcher in interface.current_oplog:  # FIXME: Workaround
            return None
            # oplog cached NoneDispatcher, which is undesirable
            # return "None" causes it to clear the cache
            # Then all the dispatchers are revisited
            # So that "None" is normally dispatched.
        if generic_isinstance(None, interface.annotation):
            return Force(None)


class SourceDispatcher(AbstractDispatcher):
    """提取 MessageEvent 消息链 Source 元素的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        from .event.message import ActiveMessage, MessageEvent

        if isinstance(interface.event, (MessageEvent, ActiveMessage)) and generic_issubclass(
            Source, interface.annotation
        ):
            return interface.event.source


class QuoteDispatcher(AbstractDispatcher):
    """提取 MessageEvent 消息链 Quote 元素的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        from .event.message import ActiveMessage, MessageEvent

        if isinstance(interface.event, (MessageEvent, ActiveMessage)) and generic_issubclass(
            Quote, interface.annotation
        ):
            return interface.event.quote


class SenderDispatcher(AbstractDispatcher):
    """从 MessageEvent 提取 sender 的 Dispatcher."""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        from .event.message import MessageEvent

        if isinstance(interface.event, MessageEvent):
            with contextlib.suppress(TypeError):
                if generic_isinstance(interface.event.sender, interface.annotation):
                    return interface.event.sender


class SubjectDispatcher(AbstractDispatcher):
    """从 ActiveMessage 提取 subject 的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        from .event.message import ActiveMessage

        if isinstance(interface.event, ActiveMessage) and generic_issubclass(
            interface.annotation, interface.event.subject
        ):
            return interface.event.subject


class BaseDispatcher(AbstractDispatcher):
    """空 Dispatcher"""

    @staticmethod
    async def catch(*_):
        pass


class FriendDispatcher(AbstractDispatcher):
    """提取 Friend 的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        if generic_issubclass(Friend, interface.annotation):
            return interface.event.friend


class GroupDispatcher(AbstractDispatcher):
    """提取 Group 的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        if generic_issubclass(Group, interface.annotation):
            return interface.event.group


class MemberDispatcher(AbstractDispatcher):
    """提取 Member 的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        if generic_issubclass(Member, interface.annotation):
            return interface.event.member
        elif generic_issubclass(Group, interface.annotation):
            return interface.event.member.group


class OperatorDispatcher(AbstractDispatcher):
    """提取 Operator 的 Dispatcher"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        if generic_issubclass(Member, interface.annotation):
            return interface.event.operator
        elif generic_issubclass(Group, interface.annotation):
            # NOTE: operator 不为 None。因为 operator 可为 None 的事件必有 group 属性，
            # 会由 dispatcher 之前的 GroupDispatcher 处理，不可能进入此处。
            return interface.event.operator.group


class OperatorMemberDispatcher(AbstractDispatcher):
    """提取 Operator 的 Dispatcher (同时有 Member 和 Operator)"""

    @staticmethod
    async def catch(interface: DispatcherInterface):
        if generic_issubclass(Member, interface.annotation):
            return interface.event.operator if interface.name == "operator" else interface.event.member
        elif generic_issubclass(Group, interface.annotation):
            return interface.event.member.group
