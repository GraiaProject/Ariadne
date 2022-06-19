from __future__ import annotations

import re
from copy import copy
from typing import Dict, FrozenSet, Iterable, List, Optional, Set, Union

from typing_extensions import Self

from ...typing import FlagAlias, Sentinel

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
R_ESCAPE = dict(reversed(ESCAPE.items()))


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
    choice: FrozenSet[str]

    def __init__(self, choice: Union[Iterable[str], str]) -> None:
        self.choice = frozenset((choice,)) if isinstance(choice, str) else frozenset(choice)

    def __repr__(self) -> str:
        return f"Text({self.choice!r})"


class BaseParam:
    __slots__ = ("names",)
    names: FrozenSet[str]

    def __init__(self, names: Iterable[str]) -> None:
        self.names = frozenset(names)

    def __repr__(self) -> str:
        return f"BaseParam({self.names!r})"


class Param:
    __slots__ = ("name", "annotation", "default", "wildcard")
    name: str
    annotation: Optional[str]
    default: Optional[str]
    wildcard: bool

    def __init__(
        self,
        name: str,
        wildcard: bool = False,
        annotation: Optional[str] = None,
        default: Optional[str] = None,
    ) -> None:
        self.name = name
        self.annotation = annotation
        self.default = default
        self.wildcard = wildcard

    def __repr__(self) -> str:
        return f"Param({'...' if self.wildcard else ''}{self.name}: {self.annotation} = {self.default})"


U_Token = Union[Text, BaseParam, Param]

ann_assign = re.compile(r"(?P<name>[^:=]+)(?P<annotation>:[^=]+)?(?P<default>=.+)?")


def parse_param(param_str: str) -> Union[BaseParam, Param]:
    wildcard: bool = param_str.startswith("...")
    if wildcard:
        param_str = param_str[3:]
    match = ann_assign.match(param_str)
    assert match, f"Invalid param: {param_str}"
    names, *extra = match.groups()
    names = names.split("|")
    if not extra:
        return BaseParam(map(str.strip, names))
    assert len(names) == 1, f"Invalid param: {param_str}"
    return Param(names[0], wildcard, *map(lambda s: unescape(s).lstrip(":=").strip(), extra))


def tokenize(string: str) -> List[U_Token]:
    """将字符串转义化, 并处理为 Text,  Param 两种 token

    Args:
        string (str): 要处理的字符串

    Returns:
        List[Tuple[CommandToken, List[int, str]]]: 处理后的 Token
    """

    string = escape(string)

    paren: str = ""
    char_stk: List[str] = []
    token: List[U_Token] = []

    def pop() -> str:
        piece = "".join(char_stk)
        char_stk.clear()
        return piece

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


def split(string: str, keep_quote: bool = False) -> List[str]:
    """尊重引号与转义的字符串切分

    Args:
        string (str): 要切割的字符串
        keep_quote (bool): 是否保留引号, 默认 False.

    Returns:
        List[str]: 切割后的字符串, 可能含有空格
    """
    result: List[str] = []
    quote = ""
    cache: List[str] = []
    for index, char in enumerate(string):
        if char in {"'", '"'}:
            if not quote:
                quote = char
            elif char == quote and index and string[index - 1] != "\\":  # is current quote, not transfigured
                quote = ""
            else:
                cache.append(char)
                continue
            if keep_quote:
                cache.append(char)
        elif not quote and char == " ":
            result.append("".join(cache))
            cache = []
        elif char != "\\":
            cache.append(char)
    if cache:
        result.append("".join(cache))
    return result


class CommandEntry:
    __slots__ = ("nodes", "tokens")

    def __init__(self, tokens: List[U_Token]) -> None:
        self.tokens = tokens
        self.nodes: List[Union[FrozenSet[str], FlagAlias]] = []
        for token in tokens:
            if isinstance(token, Text):
                self.nodes.append(token.choice)
            else:
                self.nodes.append(Sentinel)


class MatchNode:
    __slots__ = ("next", "entries")
    next: Dict[Union[str, FlagAlias], MatchNode]
    entries: List[CommandEntry]

    def __init__(self) -> None:
        self.next = {}
        self.entries = []

    def __copy__(self) -> Self:
        new_obj = self.__class__()
        new_obj.next = self.next.copy()
        new_obj.entries = self.entries.copy()
        return new_obj

    def push(self, entry: CommandEntry, index: int = 0) -> None:
        if index >= len(entry.nodes):
            self.entries.append(entry)
            return
        current: Union[FrozenSet[str], FlagAlias] = entry.nodes[index]
        if current is Sentinel:
            self.next.setdefault(current, MatchNode()).push(entry, index + 1)
        else:
            target_nodes: List[MatchNode] = []
            conflicts: Dict[MatchNode, Set[str]] = {}
            for piece, node in {piece: self.next[piece] for piece in current if piece in self.next}.items():
                conflicts.setdefault(node, set()).add(piece)
            for old_node, conflict_fields in conflicts.items():
                new_node = copy(old_node)
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
            print(fwd)
        for k, node in self.next.items():
            node._inspect(f"{fwd}.{'?' if k is Sentinel else k}")
