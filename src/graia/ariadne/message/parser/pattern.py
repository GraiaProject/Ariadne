import abc
import copy
import re
from argparse import Action
from contextvars import ContextVar
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)

from pydantic.utils import Representation

from .util import gen_flags_repr

if TYPE_CHECKING:
    from ...typing import Self
    from ..chain import MessageChain
    from ..element import Element


@dataclass(init=True, eq=True, repr=True)
class ParamPattern:
    longs: List[str]
    short: Optional[str] = None
    default: Any = None
    help_message: Optional[str] = None


@dataclass(init=True, eq=True, repr=True)
class SwitchParameter(ParamPattern):
    default: bool = False
    auto_reverse: bool = False


@dataclass(init=True, eq=True, repr=True)
class BoxParameter(ParamPattern):
    "可以被指定传入消息的参数, 但只有一个."


class Match(abc.ABC, Representation):
    pattern: str
    optional: bool
    matched: Optional[bool]
    result: Optional["MessageChain"]

    def __init__(self, pattern, optional: bool = False) -> None:
        self.pattern = pattern
        self.optional = optional
        self.result = None
        self.matched = None
        if self.__class__ == Match:
            raise ValueError("You can't instantiate Match class directly!")

    def clone(self, result: "MessageChain", matched: bool) -> "Self":
        new_instance = copy.copy(self)
        new_instance.result = result
        new_instance.matched = matched
        return new_instance

    def __repr_args__(self):
        return [
            ("matched", self.matched),
            ("result", self.result),
            ("pattern", self.pattern),
        ]

    def gen_regex(self) -> str:
        ...


class RegexMatch(Match):
    "基础的正则表达式匹配器"
    flags: re.RegexFlag
    flags_repr: str
    regex_match: Optional[re.Match]
    preserve_space: bool

    def __init__(
        self,
        pattern: str,
        *,
        optional: bool = False,
        flags: re.RegexFlag = re.RegexFlag(0),
        preserve_space: bool = True,
    ) -> None:
        super().__init__(pattern, optional)
        self.flags = flags
        self.flags_repr = gen_flags_repr(self.flags)
        self.regex_match = None
        self.preserve_space = preserve_space

    def gen_regex(self) -> str:
        return (
            f"({f'?{self.flags_repr}:' if self.flags_repr else ''}{self.pattern})"
            f"{'?' if self.optional else ''}{'( )?' if self.preserve_space else ''}"
        )

    def clone(
        self, result: "MessageChain", matched: bool, re_match: Optional[re.Match] = None
    ) -> "Self":
        new_instance: RegexMatch = super().clone(result, matched)
        new_instance.regex_match = re_match
        return new_instance


class WildcardMatch(Match):
    """泛匹配."""

    preserve_space: bool

    def __init__(
        self, greed: bool = True, optional: bool = False, preserve_space: bool = True
    ) -> None:
        super().__init__(f".*", optional=optional)
        self.greed = greed
        self.preserve_space = preserve_space

    def gen_regex(self) -> str:
        return f"({self.pattern}{'?' if self.greed else ''}){'?' if self.optional else ''}{'( )?' if self.preserve_space else ''}"


class FullMatch(Match):
    """全匹配."""

    def __init__(
        self, pattern: str, *, optional: bool = False, preserve_space: bool = True
    ) -> None:
        super().__init__(pattern, optional)
        self.preserve_space = preserve_space

    def gen_regex(self) -> str:
        return f"({re.escape(self.pattern)}){'?' if self.optional else ''}{'( )?' if self.preserve_space else ''}"


class ElementMatch(Match):
    """元素类型匹配."""

    pattern: Type["Element"]
    result: "Element"

    def __init__(
        self,
        pattern: Type["Element"],
        optional: bool = False,
        preserve_space: bool = True,
    ) -> None:
        super().__init__(pattern, optional=optional)
        self.preserve_space = preserve_space

    def gen_regex(self) -> str:
        return (
            f"(\x02\\d+_{self.pattern.__fields__['type'].default}\x03){'?' if self.optional else ''}"
            f"{'( )?' if self.preserve_space else ''}"
        )


T_const = TypeVar("T_const")
T_default = TypeVar("T_default")


class ArgumentMatch(Match):
    """参数匹配."""

    pattern: Sequence[str]
    name: str
    nargs: Union[str, int]
    action: Union[str, Type[Action]]
    const: Optional[T_const]
    default: Optional[T_default]
    regex: Optional[re.Pattern]
    result: Union["MessageChain", Any]
    add_arg_data: Dict[str, Any]
    elem_mapping_ctx: ContextVar["MessageChain"] = ContextVar("elem_mapping_ctx")

    def __init__(
        self,
        *pattern: str,
        optional: bool = True,
        const: Optional[T_const] = ...,
        default: Optional[T_default] = ...,
        nargs: Union[str, int] = ...,
        action: Union[str, Type[Action]] = ...,
        regex: Optional[str] = None,
    ) -> None:
        if not pattern:
            raise ValueError("Expected at least 1 pattern!")
        super().__init__(pattern, optional)
        self.name = pattern[0].lstrip("-").replace("-", "_")
        self.nargs = nargs
        self.action = action
        self.const = const
        self.default = default
        self.regex = re.compile(regex) if regex else None
        data: Dict[str, Any] = {}
        if action is not ...:
            data["action"] = action
        if nargs is not ...:
            data["nargs"] = nargs
        if const is not ...:
            data["const"] = const
        if default is not ...:
            data["default"] = default
        if pattern[0].startswith("-"):
            data["required"] = not optional
        self.add_arg_data = data
