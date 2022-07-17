import inspect
import weakref
from enum import Enum
from typing import (
    ClassVar,
    Dict,
    Generic,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)

from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.decorator import DecoratorInterface
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from ..dispatcher import SenderDispatcher
from ..model.relationship import Friend, Group, Member, Stranger
from ..typing import generic_issubclass

U_User = Union[Friend, Member, Stranger]


class ScopeType(Enum):
    Group = "Group"
    Friend = "Friend"
    Member = "Member"
    User = "User"
    Event = "Event"
    Global = "Global"
    Module = "Module"
    Custom = "Custom"


ScopeTypeLiteral = Literal["Group", "Friend", "Member", "User", "Event", "Global", "Module", "Custom"]


class ScopedStorage(dict):
    ...


T_Storage = TypeVar("T_Storage", bound=Type[dict])


class ScopedContext(Decorator, BaseDispatcher, Generic[T_Storage]):
    pre = True
    context_storage: ClassVar[Dict[ScopeType, dict]] = {}
    scope_type: ScopeType
    storage_type: T_Storage
    src: Optional[str]

    @overload
    def __init__(
        self, scope_type: Literal[ScopeType.Custom], storage_type: T_Storage = ScopedStorage, src: str = "#"
    ):
        ...

    @overload
    def __init__(
        self,
        scope_type: Union[
            Literal[ScopeType.Group, ScopeType.Friend, ScopeType.Member, ScopeType.Module, ScopeType.Global],
            ScopeTypeLiteral,
        ] = ScopeType.Module,
        storage_type: T_Storage = ScopedStorage,
    ):
        ...

    def __init__(
        self,
        scope_type: Union[ScopeType, ScopeTypeLiteral] = ScopeType.Module,
        storage_type: T_Storage = ScopedStorage,
        src: Optional[str] = None,
    ):
        if not isinstance(scope_type, ScopeType):
            scope_type = ScopeType[scope_type]
        self.scope_type = scope_type
        if scope_type is not ScopeType.Custom:
            assert src is None
        self.src = src
        if scope_type is ScopeType.Module:
            # get caller's module
            outer_frame = inspect.stack()[1]
            module_name = outer_frame.frame.f_globals["__name__"]
            self.src = module_name
        self.storage_type = storage_type

    async def lookup(self, interface: DispatcherInterface):
        scope_dict: dict = self.context_storage.setdefault(self.scope_type, {})
        if self.scope_type is ScopeType.Group:
            group: Group = await interface.lookup_param("group", Group, None)
            return scope_dict.setdefault(group.id, {})
        if self.scope_type is ScopeType.Friend:
            friend: Friend = await interface.lookup_param("friend", Friend, None)
            return scope_dict.setdefault(friend.id, {})
        if self.scope_type is ScopeType.Member:
            member: Member = await interface.lookup_param("member", Member, None)
            return scope_dict.setdefault((member.group.id, member.id), {})
        if self.scope_type is ScopeType.User:
            user: U_User = await interface.lookup_by_directly(SenderDispatcher, "user", U_User, None)
            return scope_dict.setdefault(user.id, {})
        if self.scope_type is ScopeType.Event:
            event = interface.event
            if id(event) not in scope_dict:
                scope_dict[id(event)] = {}
                weakref.finalize(event, lambda d: self.context_storage[ScopeType.Event].pop(d), id(event))
            return scope_dict[id(event)]
        if self.scope_type is ScopeType.Global:
            return scope_dict
        if self.scope_type is ScopeType.Module:
            return scope_dict.setdefault(self.src, {})
        if self.scope_type is ScopeType.Custom:
            return scope_dict.setdefault(self.src, {})

    async def catch(self, interface: DispatcherInterface):
        if not generic_issubclass(self.storage_type, interface.annotation):
            return
        return await self.lookup(interface)

    async def target(self, interface: DecoratorInterface):
        return await self.lookup(interface.dispatcher_interface)
