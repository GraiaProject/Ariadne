from __future__ import annotations

import abc
import functools
import inspect
import re
from contextvars import ContextVar
from typing import Any, Generic, Iterable, List, MutableMapping, TypeVar, Union
from typing_extensions import Self
from weakref import WeakKeyDictionary, WeakSet

from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from ...typing import MaybeFlag, Sentinel, T
from ..chain import MessageChain
from ..element import Element, Plain, Quote, Source

L_PAREN = ("{", "[")
R_PAREN = ("}", "]")
ESCAPE = {
    "\\": "\x00",
    "[": "\x01",
    "]": "\x02",
    "{": "\x03",
    "}": "\x04",
    "|": "\x05",
}
R_ESCAPE = {v: k for k, v in ESCAPE.items()}


def escape(string: str) -> str:
    """转义字符串

    Args:
        string (str): 要转义的字符串

    Returns:
        str: 转义后的字符串
    """
    for k, v in ESCAPE.items():
        string = string.replace("\\" + k, v)
    string = string.replace("\\", "")
    return string


def unescape(string: str) -> str:
    """逆转义字符串, 自动去除空白符

    Args:
        string (str): 要逆转义的字符串

    Returns:
        str: 逆转义后的字符串
    """
    for k, v in R_ESCAPE.items():
        string = string.replace(k, v)
    return string.strip()


class Text:
    __slots__ = "choice"
    choice: frozenset[str]

    def __init__(self, choice: Iterable[str] | str) -> None:
        self.choice = frozenset((choice,)) if isinstance(choice, str) else frozenset(choice)

    def __repr__(self) -> str:
        return f"Text({self.choice!r})"


class Param:
    __slots__ = ("names",)
    names: frozenset[str]

    def __init__(self, names: Iterable[str]) -> None:
        self.names = frozenset(names)

    def __repr__(self) -> str:
        return f"Param({self.names!r})"


class AnnotatedParam:
    __slots__ = ("name", "annotation", "default", "wildcard")
    name: str
    annotation: str | None
    default: str | None
    wildcard: bool

    def __init__(
        self,
        name: str,
        wildcard: bool = False,
        annotation: str | None = None,
        default: str | None = None,
    ) -> None:
        self.name = name
        self.annotation = annotation
        self.default = default
        self.wildcard = wildcard

    def __repr__(self) -> str:
        return (
            f"AnnotatedParam({'...' if self.wildcard else ''}{self.name}: {self.annotation} = {self.default})"
        )

    def to_param(self) -> Param:
        return Param((self.name,))


U_Token = Union[Text, Param, AnnotatedParam]

ann_assign = re.compile(r"(?P<name>[^:=]+)(?P<annotation>:[^=]+)?(?P<default>=.+)?")


def parse_param(param_str: str) -> Param | AnnotatedParam:
    wildcard: bool = param_str.startswith("...")
    if wildcard:
        param_str = param_str[3:]
    match = ann_assign.match(param_str)
    assert match, f"Invalid param: {param_str}"
    names, *extra = match.groups()
    names = [unescape(name).strip() for name in names.split("|")]
    if not wildcard and not any(extra):
        return Param(names)
    assert len(names) == 1, f"Invalid param: {param_str}"
    return AnnotatedParam(
        names[0], wildcard, *(unescape(s).strip().lstrip(":=").strip() if s else None for s in extra)
    )


def _pop(char_stk: list[str]) -> str:
    piece = "".join(char_stk)
    char_stk.clear()
    return piece


def tokenize(string: str) -> list[U_Token]:
    """将字符串转义化, 并处理为 Text,  Param 两种 token

    Args:
        string (str): 要处理的字符串

    Returns:
        List[Tuple[CommandToken, List[int, str]]]: 处理后的 Token
    """

    string = escape(string)

    paren: str = ""
    char_stk: list[str] = []
    token: list[U_Token] = []
    pop = functools.partial(_pop, char_stk)

    for index, char in enumerate(string):
        if char in L_PAREN + R_PAREN:
            if char in L_PAREN:
                assert not paren, (
                    f"""Duplicated parenthesis character "{char}" @ {index} !"""
                    """Are you sure you've escaped with "\\"?"""
                )
                paren = char
            elif char in R_PAREN:
                piece = pop()
                assert paren, f"No matching parenthesis: {paren} @ {index}"
                if paren == "[":  # CHOICE
                    token.append(Text(unescape(x) for x in piece.split("|")))
                elif paren == "{":  # PARAM
                    token.append(parse_param(piece))
                paren = ""
        elif char == " " and not paren:
            if char_stk:
                token.append(Text(pop()))
        else:
            char_stk.append(char)

    assert not paren, f"Unclosed parenthesis: {paren}"

    if char_stk:
        token.append(Text(pop()))

    return token


class MatchEntry:
    def __init__(self, tokens: list[U_Token]) -> None:
        self.nodes: list[MaybeFlag[frozenset[str]]] = [
            token.choice if isinstance(token, Text) else Sentinel for token in tokens
        ]
        self.tokens: list[Text | Param] = [
            token.to_param() if isinstance(token, AnnotatedParam) else token for token in tokens
        ]
        self.params: list[Param] = [token for token in self.tokens if isinstance(token, Param)]


T_MatchEntry = TypeVar("T_MatchEntry", bound=MatchEntry)


class MatchNode(Generic[T_MatchEntry]):
    __slots__ = ("next", "entries")
    next: dict[MaybeFlag[str], MatchNode[T_MatchEntry]]
    entries: WeakSet[T_MatchEntry]

    def __init__(self) -> None:
        self.next = {}
        self.entries = WeakSet()

    def copy(self) -> Self:
        new_obj = self.__class__()
        new_obj.next = self.next.copy()
        new_obj.entries = self.entries.copy()
        return new_obj

    def push(self, entry: T_MatchEntry, index: int = 0) -> None:
        if index >= len(entry.nodes):
            self.entries.add(entry)
            return
        current: MaybeFlag[frozenset[str]] = entry.nodes[index]
        if current is Sentinel:
            self.next.setdefault(current, MatchNode()).push(entry, index + 1)
        else:
            target_nodes: list[MatchNode[T_MatchEntry]] = []
            conflicts: dict[MatchNode[T_MatchEntry], set[str]] = {}
            for piece, node in {piece: self.next[piece] for piece in current if piece in self.next}.items():
                conflicts.setdefault(node, set()).add(piece)
            for old_node, conflict_fields in conflicts.items():
                new_node = old_node.copy()
                target_nodes.append(new_node)
                for field in conflict_fields:
                    self.next[field] = new_node
                new_node.push(entry, index + 1)
                current -= conflict_fields
            if current:
                new_node = MatchNode()
                new_node.push(entry, index + 1)
                for field in current:
                    self.next[field] = new_node

    def _inspect(self, fwd=""):
        if not self.next:
            pass
        for k, node in self.next.items():
            node._inspect(f"{fwd}{'<PARAM>' if k is Sentinel else k} ")


class raw(abc.ABC):  # wildcard annotation object
    ...


raw.register(MessageChain)


def convert_empty(obj: T) -> MaybeFlag[T]:
    if obj is inspect.Parameter.empty:
        return Sentinel
    if isinstance(obj, Decorator):
        return Sentinel
    return obj


class ContextVarDispatcher(BaseDispatcher):
    """分发常量给指定名称的参数"""

    def __init__(self, data_ctx: ContextVar[dict[str, Any]]) -> None:
        self.data_ctx = data_ctx

    async def catch(self, interface: DispatcherInterface):
        return self.data_ctx.get().get(interface.name)


ChainContent = List[Union[str, Element]]

ChainContentList = List[ChainContent]

split_cache: MutableMapping[MessageChain, ChainContentList] = WeakKeyDictionary()

quote_pairs = {"'": "'", '"': '"', "‘": "’", "“": "”"}


def extract_str(buf: ChainContent) -> str | None:
    if len(buf) == 1 and isinstance(buf[0], str):
        return buf[0]


def split(chain: MessageChain) -> ChainContentList:
    if chain in split_cache:
        return split_cache[chain]
    result: ChainContentList = []
    quote: str = ""
    buffer: ChainContent = []

    for elem in chain.__root__:
        if elem.__class__ in (Quote, Source):
            continue
        if not isinstance(elem, Plain):
            buffer.append(elem)
            continue
        cache: list[str] = []
        skipping: bool = False
        for char in elem.text:
            if char == "\\" or skipping:
                skipping = not skipping
                continue
            if char in quote_pairs and not quote:
                quote = quote_pairs[char]
                continue
            elif char == quote:
                quote = ""
                continue
            if char == " " and (cache or buffer) and not quote:
                if cache:
                    buffer.append("".join(cache))
                    cache.clear()
                if buffer:
                    result.append(buffer)
                    buffer = []  # buffer is "move"d, so DO NOT clear.
            elif quote or char != " ":
                cache.append(char)
        if cache:
            buffer.append("".join(cache))
    if buffer:
        result.append(buffer)
    split_cache[chain] = result
    return result
