import functools
import heapq
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Optional,
    Protocol,
    Union,
)

from pydantic.utils import Representation

from graia.ariadne.model import Friend, Group, Member, Stranger

from ..typing import T

SALT = hash("Graia_Permission_Salt") % (2**16)


class Key(Representation):
    __slots__ = ("keys",)

    def __init__(self, key: str) -> None:
        if key:
            self.keys = tuple(key.split("."))
        else:
            self.keys = ()

    def __hash__(self) -> int:
        return hash(self.keys)

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Key):
            return False
        return self.keys == __o.keys

    def parent(self) -> Optional["Key"]:
        if len(self.keys):
            return Key(".".join(self.keys[:-1]))

    def __add__(self, __o: "Key") -> "Key":
        return Key(".".join(self.keys + __o.keys))

    def gen(self) -> Iterable["Key"]:
        yield self
        if len(self.keys):
            yield from self.parent().gen()


class SupportsLess(Protocol):
    def __lt__(self, other: Any) -> bool:
        ...


class _HeapItem(SupportsLess, Generic[T]):
    __slots__ = ("key", "value")

    def __init__(self, key: Key, value: T) -> None:
        self.key = key
        self.value = value

    def __lt__(self, other: "_HeapItem") -> bool:
        return self.key < other.key


class Heap(Generic[T]):
    def __init__(self, key: Callable[[T], SupportsLess] = ..., seq: Optional[List[T]] = None):
        self.key = key
        self._heap: List[_HeapItem[T]] = []
        if seq:
            for item in seq:
                heapq.heappush(self._heap, _HeapItem(key(item), item))

    def push(self, item: T) -> None:
        heapq.heappush(self._heap, _HeapItem(self.key(item), item))

    def pop(self) -> T:
        return heapq.heappop(self._heap).value


@functools.singledispatch
def get_key(obj: Any) -> Key:
    return Key("")


@get_key.register
def _(obj: str) -> Key:
    return Key(obj)


@get_key.register
def _(obj: Friend) -> Key:
    return Key(f"user.{obj.id}")


@get_key.register
def _(obj: Stranger) -> Key:
    return Key(f"user.{obj.id}")


@get_key.register
def _(obj: Group) -> Key:
    return Key(f"group.{obj.id}")


@get_key.register
def _(obj: Member) -> Key:
    return Key(f"group.{obj.group.id}.user.{obj.id}")


ScopeAnnotation = Union[None, Friend, Member, Stranger, Literal["user", "group"]]


class ValueTree:
    def __init__(self):
        self.nodes: Dict[Key, int] = {}

    def set(self, key: Key, value: int) -> None:
        self.nodes[key] = value

    def get(self, key: Key) -> int:
        for val_key in key.gen():
            if val_key in self.nodes:
                return self.nodes[val_key]


class PermissionManager:
    def __init__(self) -> None:
        self.nodes: Dict[Key, ValueTree] = {}

    def set(self, key: str, value: int, scope: ScopeAnnotation = None) -> None:
        scope_key = get_key(scope)
        self.nodes.setdefault(scope_key, ValueTree())
        self.nodes[scope_key].set(Key(key), value)

    def get(self, key: str, scope: ScopeAnnotation = None) -> int:
        sub_scope_key = get_key(scope)
        sub_name_key = Key(key)
        for scope_key in sub_scope_key.gen():
            if scope_key in self.nodes:
                res = self.nodes[scope_key].get(sub_name_key)
                if res is not None:
                    return res
