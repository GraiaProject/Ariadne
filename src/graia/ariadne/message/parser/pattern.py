import abc
import copy
import re
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
)

from graia.ariadne.message.chain import ELEMENT_MAPPING

if TYPE_CHECKING:
    from ..chain import MessageChain
    from ..element import Element

    Self = TypeVar("Self")


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


class Match(abc.ABC):
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

    def __repr__(self) -> str:
        annotation = {k: getattr(self, k) for k in self.__annotations__.keys()}
        return f"<{self.__class__.__qualname__} {annotation})>"

    def clone(self, result: "MessageChain", matched: bool) -> "Self":
        new_instance = copy.copy(self)
        new_instance.result = result
        new_instance.matched = matched
        return new_instance

    def gen_regex(self) -> str:
        ...


def gen_flags_repr(flags: re.RegexFlag) -> str:
    flags_list: List[str] = []
    if re.ASCII in flags:
        flags_list.append("a")
    if re.IGNORECASE in flags_list:
        flags_list.append("i")
    if re.LOCALE in flags_list:
        flags_list.append("L")
    if re.MULTILINE in flags_list:
        flags_list.append("m")
    if re.DOTALL in flags_list:
        flags_list.append("s")
    if re.UNICODE in flags_list:
        flags_list.append("u")
    if re.VERBOSE in flags_list:
        flags_list.append("x")


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


class FullMatch(Match):
    def __init__(
        self, pattern: str, *, optional: bool = False, preserve_space: bool = True
    ) -> None:
        super().__init__(pattern, optional)
        self.preserve_space = preserve_space

    def gen_regex(self) -> str:
        return f"({re.escape(self.pattern)}){'?' if self.optional else ''}{'( )?' if self.preserve_space else ''}"


class ElementMatch(Match):
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
            f"(\b\\d+_{self.pattern.__fields__['type'].default}\b){'?' if self.optional else ''}"
            f"{'( )?' if self.preserve_space else ''}"
        )


class ArgumentMatch(Match):
    pattern: Iterable[str]
    name: str
    nargs: Literal["?", "+", "*"]
    action: str
    const: Optional[Any]
    default: Optional[Any]
    regex: Optional[str]
    result: Union["MessageChain", Any]

    def __init__(
        self,
        *pattern: str,
        optional: bool = True,
        const: Optional[Any] = None,
        default: Optional[Any] = None,
        nargs: Literal["?", "+", "*", "N"] = "?",
        action: str = "store",
        regex: Optional[str] = None,
    ) -> None:
        if not all(string.startswith("-") for string in pattern):
            raise ValueError("Invalid pattern: pattern without '-' as start!")
        elif not pattern:
            raise ValueError("Expected as least 1 pattern!")
        super().__init__(pattern, optional)
        self.name = pattern[0].lstrip("-").replace("-", "_")
        self.nargs = nargs
        self.action = action
        self.const = const
        self.default = default
        self.regex = re.compile(regex) if regex else None
