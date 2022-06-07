from typing import Generic, Optional, Sequence, Set, Type, Union

from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.exceptions import ExecutionStop, RequirementCrashed
from graia.broadcast.interfaces.decorator import DecoratorInterface

from ..message.chain import MessageChain
from ..message.element import Quote, Source
from ..model import BotMessage, Friend, Group, Member
from ..typing import T


class Certain(Decorator, Generic[T]):

    pre = True

    def __init__(self, value: T, annotation: Optional[Type[T]] = None) -> None:
        self.value: T = value
        self.annotation: Type[T] = annotation or value.__class__

    async def target(self, i: DecoratorInterface):
        try:
            val: T = await i.dispatcher_interface.lookup_param(
                "__decorator_parameter__", self.annotation, None
            )
        except RequirementCrashed as e:
            raise ExecutionStop from e
        if not self.comp(val):
            raise ExecutionStop
        return val

    def comp(self, value: T) -> bool:
        return value == self.value


SequenceOrInstance = Union[Sequence[T], T]


class CertainGroup(Certain):
    """需要消息发送/事件触发在指定群组"""

    value: Set[int]

    def __init__(self, group: SequenceOrInstance[Union[Group, int]]):
        group = list(group) if isinstance(group, Sequence) else [group]
        super().__init__({int(g) for g in group}, Group)

    def comp(self, value: Group) -> bool:
        return value.id in self.value


class CertainFriend(Certain):
    """需要消息发送者/事件触发者是指定好友"""

    value: Set[int]

    def __init__(self, friend: SequenceOrInstance[Union[Friend, int]]):
        friend = list(friend) if isinstance(friend, Sequence) else [friend]
        super().__init__({int(f) for f in friend}, Friend)

    def comp(self, value: Friend) -> bool:
        return value.id in self.value


class CertainMember(Certain):
    """需要发送者/事件触发者是指定群员"""

    value: Set[int]
    group: Optional[Set[int]]

    def __init__(
        self,
        member: SequenceOrInstance[Union[Member, int]],
        group: Optional[SequenceOrInstance[Union[Member, int]]] = None,
    ):
        member = list(member) if isinstance(member, Sequence) else [member]
        super().__init__({int(m) for m in member}, Member)
        self.group = None
        if group:
            group = list(group) if isinstance(group, Sequence) else [group]
            self.group = {int(g) for g in group}

    def comp(self, value: Member) -> bool:
        return value.id in self.value and (not self.group or value.group.id in self.group)


class Quoting(Decorator):
    """需要回复指定的消息"""

    pre = True

    msg_ids: Set[int]

    def __init__(self, message: SequenceOrInstance[Union[int, BotMessage, MessageChain, Source]]):
        if not isinstance(message, Sequence):
            message = [message]
        self.msg_ids = set()
        for msg in message:
            if isinstance(msg, BotMessage):
                self.msg_ids.add(msg.messageId)
            elif isinstance(msg, MessageChain):
                self.msg_ids.add(msg.get_first(Quote).id)
            elif isinstance(msg, Source):
                self.msg_ids.add(msg.id)
            else:
                self.msg_ids.add(msg)

    async def target(self, i: DecoratorInterface):
        try:
            msg_chain: MessageChain = await i.dispatcher_interface.lookup_param(
                "__decorator_parameter__", MessageChain, None
            )
            quotes = msg_chain.get(Quote)
            if not quotes or quotes[0].id not in self.msg_ids:
                raise RequirementCrashed
        except RequirementCrashed as e:
            raise ExecutionStop from e
        return msg_chain
