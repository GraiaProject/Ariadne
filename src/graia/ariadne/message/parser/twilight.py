import abc
import enum
import re
import string
from argparse import Action
from copy import copy, deepcopy
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypedDict,
    TypeVar,
    Union,
    final,
    overload,
)

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from loguru import logger
from pydantic.utils import Representation

from ..chain import MessageChain
from ..element import Element
from .util import (
    ElementType,
    MessageChainType,
    TwilightParser,
    elem_mapping_ctx,
    split,
    transformed_regex,
)

# ------ Match ------


class Match(abc.ABC, Representation):
    """匹配器的抽象基类."""

    pattern: str
    optional: bool
    help: str
    matched: Optional[bool]
    result: Optional["MessageChain"]

    def __init__(self, pattern, optional: bool = False, help: str = "", alt_help: str = "") -> None:
        self.pattern = pattern
        self.optional = optional
        self.help = help
        self.result = None
        self.matched = None
        self.alt_help = alt_help
        if self.__class__ == Match:
            raise ValueError("You can't instantiate Match class directly!")

    def __repr_args__(self):
        return [
            ("matched", self.matched),
            ("result", self.result),
            ("pattern", self.pattern),
        ]


class SpacePolicy(str, enum.Enum):
    NOSPACE = ""
    PRESERVE = "( )?"
    FORCE = "( )"

    def __init__(self, src: str) -> None:
        self.src = src


NOSPACE = SpacePolicy.NOSPACE
PRESERVE = SpacePolicy.PRESERVE
FORCE = SpacePolicy.FORCE


class RegexMatch(Match):
    """基础的正则表达式匹配."""

    regex_match: Optional[re.Match]
    space: SpacePolicy

    def __init__(
        self,
        pattern: str,
        *,
        optional: bool = False,
        flags: re.RegexFlag = re.RegexFlag(0),
        space: SpacePolicy = SpacePolicy.PRESERVE,
        help: str = "",
        alt_help: str = "",
        preserve_space: bool = ...,
    ) -> None:
        super().__init__(pattern=pattern, optional=optional, help=help, alt_help=alt_help)
        self.flags = flags
        self.regex_match = None
        self.space = space
        if preserve_space is not ...:
            logger.warning('"preserve_space argument" is deprecated and will be removed in 0.5.2!')
            logger.warning('use "space" instead!')
            self.space = SpacePolicy.PRESERVE if preserve_space else SpacePolicy.NOSPACE

    @final
    def gen_regex(self) -> str:
        return (
            f"{transformed_regex(self.flags, self.regex_src)}"
            f"{'?' if self.optional else ''}{self.space.src}"
        )

    @property
    def regex_src(self) -> str:
        return self.pattern

    def get_help(self) -> str:
        return self.pattern.replace("( )?", " ") if not self.alt_help else self.alt_help


class ParamMatch(RegexMatch):
    """与 WildcardMatch 类似, 但需要至少一个字符. 且仅匹配用空格分开的一段. (不支持输入的转义处理, 但是可以处理不同引号包裹)"""

    def __init__(
        self,
        *,
        optional: bool = False,
        flags: re.RegexFlag = re.RegexFlag(0),
        space: SpacePolicy = SpacePolicy.PRESERVE,
        help: str = "",
        alt_help: str = "",
        preserve_space: bool = ...,
    ) -> None:
        super().__init__(
            r"""(?:").+?(?:")|(?:').+?(?:')|\b[^ ]+?\b""",
            optional=optional,
            flags=flags,
            space=space,
            help=help,
            alt_help=alt_help,
            preserve_space=preserve_space,
        )

    def get_help(self) -> str:
        return "PARAM"


class WildcardMatch(RegexMatch):
    """泛匹配."""

    greed: bool

    def __init__(
        self,
        *,
        greed: bool = True,
        optional: bool = False,
        flags: re.RegexFlag = re.RegexFlag(0),
        space: SpacePolicy = SpacePolicy.PRESERVE,
        help: str = "",
        alt_help: str = "",
        preserve_space: bool = ...,
    ) -> None:
        super().__init__(
            ".*",
            optional=optional,
            flags=flags,
            space=space,
            help=help,
            alt_help=alt_help,
            preserve_space=preserve_space,
        )
        self.greed = greed

    @property
    def regex_src(self) -> str:
        return f"{self.pattern}{'?' if not self.greed else ''}"


class FullMatch(RegexMatch):
    """全匹配."""

    @property
    def regex_src(self) -> str:
        return re.escape(self.pattern)

    def get_help(self) -> str:
        return self.pattern


class ElementMatch(RegexMatch):
    """元素类型匹配."""

    pattern: Type["Element"]
    result: "Element"

    def __init__(
        self,
        pattern: Type["Element"],
        *,
        optional: bool = False,
        flags: re.RegexFlag = re.RegexFlag(0),
        space: SpacePolicy = SpacePolicy.PRESERVE,
        help: str = "",
        alt_help: str = "",
        preserve_space: bool = ...,
    ) -> None:
        super().__init__(
            pattern,
            optional=optional,
            flags=flags,
            space=space,
            help=help,
            alt_help=alt_help,
            preserve_space=preserve_space,
        )

    @property
    def regex_src(self) -> str:
        return f"\x02\\d+_{self.pattern.__fields__['type'].default}\x03"

    def get_help(self) -> str:
        return self.pattern.__name__ if not self.alt_help else self.alt_help


class UnionMatch(RegexMatch):
    """多重匹配."""

    pattern: Tuple[str, ...]

    def __init__(
        self,
        *pattern: str,
        optional: bool = False,
        flags: re.RegexFlag = re.RegexFlag(0),
        space: SpacePolicy = SpacePolicy.PRESERVE,
        help: str = "",
        alt_help: str = "",
        preserve_space: bool = ...,
    ) -> None:
        super().__init__(
            pattern,
            optional=optional,
            flags=flags,
            space=space,
            help=help,
            alt_help=alt_help,
            preserve_space=preserve_space,
        )

    @property
    def regex_src(self) -> str:
        return f"{'|'.join(re.escape(i) for i in self.pattern)}"

    def get_help(self) -> str:
        return f"[{'|'.join(self.pattern)}]" if not self.alt_help else self.alt_help


class ArgumentMatch(Match):
    """参数匹配."""

    pattern: Sequence[str]
    name: str
    nargs: Union[str, int]
    action: Union[str, Type[Action]]
    dest: Optional[str]
    choices: Optional[Iterable]
    const: Any
    default: Any
    regex: Optional[re.Pattern]
    result: Union["MessageChain", Any]
    add_arg_data: Dict[str, Any]

    def __init__(
        self,
        *pattern: str,
        optional: bool = True,
        action: Union[str, Type[Action]] = ...,
        nargs: Union[int, str] = ...,
        const: Any = ...,
        default: Any = ...,
        type: Callable[[str], Any] = ...,
        choices: Optional[Iterable] = ...,
        help: Optional[str] = ...,
        dest: Optional[str] = ...,
        regex: Optional[str] = ...,
    ) -> None:
        if not pattern:
            raise ValueError("Expected at least 1 pattern!")
        super().__init__(pattern, optional, help)
        self.name = pattern[0].lstrip("-").replace("-", "_")
        self.nargs = nargs
        self.action = action
        self.const = const
        self.default = default
        self.choices = choices
        self.dest = dest
        self.regex = re.compile(regex) if regex is not ... else None
        data: Dict[str, Any] = {}
        if action is not ...:
            data["action"] = action
        if nargs is not ...:
            data["nargs"] = nargs
        if const is not ...:
            data["const"] = const
        if default is not ...:
            data["default"] = default
        if type is not ...:
            data["type"] = type
        if help is not ...:
            data["help"] = help
        if dest is not ...:
            data["dest"] = dest
        if choices is not ...:
            data["choices"] = choices
        if pattern[0].startswith("-"):
            data["required"] = not optional
        self.add_arg_data = data


T_Match = TypeVar("T_Match", bound=Match)

T_RMatch = TypeVar("T_RMatch", bound=RegexMatch)
# -------------------


class Sparkle(Representation):
    __dict__: Dict[str, Match]

    _description: str = ""
    _epilog: str = ""

    def __repr_args__(self):
        check = [(None, [item[0] for item in self._list_check_match])]
        return (
            check
            + [(k, v) for k, (v, _) in self._mapping_regex_match.items()]
            + list(self._mapping_arg_match.items())
        )

    @overload
    def __getitem__(self, item: Union[str, int]) -> Match:
        ...

    @overload
    def __getitem__(self, item: Type[T_Match]) -> List[T_Match]:
        ...

    @overload
    def __getitem__(self, item: Tuple[T_RMatch, int]) -> T_RMatch:
        ...

    def __getitem__(self, item: Union[str, int, Type[T_Match], Tuple[Type[T_RMatch], int]]):
        return self.get_match(item)

    def __init_subclass__(cls, /, *, description: str = "", epilog: str = "", **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._description = description
        cls._epilog = epilog

    def __getattribute__(self, _name: str):
        obj = super().__getattribute__(_name)
        if not isinstance(obj, Match):
            return obj
        else:
            return self.get_match(_name)

    @overload
    def get_match(self, item: Union[str, int]) -> Match:
        ...

    @overload
    def get_match(self, item: Type[T_Match]) -> List[T_Match]:
        ...

    @overload
    def get_match(self, item: Tuple[T_RMatch, int]) -> T_RMatch:
        ...

    def get_match(self, item: Union[str, int, Type[T_Match], Tuple[Type[T_RMatch], int]]):
        if isinstance(item, int):
            return self._list_check_match[item][0]
        elif isinstance(item, str):
            if item in self._mapping_arg_match:
                return self._mapping_arg_match[item]
            elif item in self._mapping_regex_match:
                return self._mapping_regex_match[item][0]
            else:
                raise KeyError(f"Unable to find match named {item}")
        elif isinstance(item, type):
            return self._match_ref[item]
        elif isinstance(item, tuple):
            typ, ind = item
            return self._match_ref[typ][ind]

    def __deepcopy__(self, memo):
        copied = copy(self)

        copied._list_check_match = deepcopy(self._list_check_match, memo)
        copied._mapping_arg_match = deepcopy(self._mapping_arg_match, memo)
        copied._mapping_regex_match = deepcopy(self._mapping_regex_match, memo)
        copied._parser_ref = deepcopy(self._parser_ref, memo)
        copied._match_ref = deepcopy(self._match_ref, memo)

        return copied

    @overload
    def __init__(self, check: Dict[str, Match]):
        ...

    @overload
    def __init__(
        self,
        check: Iterable[RegexMatch] = (),
        match: Optional[Dict[str, Match]] = None,
    ):
        ...

    def __init__(
        self,
        check: Iterable[RegexMatch] = (),
        match: Optional[Dict[str, Match]] = None,
        description: str = "",
        epilog: str = "",
    ):
        self._description = description or self._description
        self._epilog = epilog or self._epilog

        if isinstance(check, dict):
            match, check = check, match  # swap
            check: Iterable[RegexMatch]
            match: Dict[str, Match]

        if check is ... or not check:
            check = ()
        if match is ... or not match:
            match = {}

        match_map = {k: v for k, v in self.__class__.__dict__.items() if isinstance(v, Match)}
        match_map.update(match)

        # ----
        # ordinary matches
        # ----

        group_cnt: int = 0
        match_pattern_list: List[str] = []

        self._match_ref: DefaultDict[Type[T_Match], List[T_Match]] = DefaultDict(lambda: list())

        self._mapping_regex_match: Dict[str, Tuple[RegexMatch, int]] = {}
        self._mapping_arg_match: Dict[str, ArgumentMatch] = {}
        self._parser_ref: Dict[str, ArgumentMatch] = {}

        for v in check:
            self._match_ref[v.__class__].append(v)

        self._parser = TwilightParser(prog="", add_help=False)
        for k, v in match_map.items():
            if k.startswith("_") or k[0] in string.digits:
                raise ValueError("Invalid Match object name!")

            self._match_ref[v.__class__].append(v)

            if isinstance(v, ArgumentMatch):  # add to self._parser
                self._mapping_arg_match[k] = v
                if v.action is ... or self._parser.accept_type(v.action):
                    if "type" not in v.add_arg_data or v.add_arg_data["type"] is MessageChain:
                        v.add_arg_data["type"] = MessageChainType(v.regex)
                    elif isinstance(v.add_arg_data["type"], type) and issubclass(
                        v.add_arg_data["type"], Element
                    ):
                        v.add_arg_data["type"] = ElementType(v.add_arg_data["type"])
                action = self._parser.add_argument(*v.pattern, **v.add_arg_data)
                v.dest = action.dest
                self._parser_ref[v.dest] = v

            elif isinstance(v, RegexMatch):  # add to self._mapping_regex_match
                self._mapping_regex_match[k] = (v, group_cnt + 1)
                group_cnt += re.compile(v.gen_regex()).groups
                match_pattern_list.append(v.gen_regex())

            else:
                raise ValueError(f"{v} is neither RegexMatch nor ArgumentMatch!")

        if (
            not all(v.pattern[0].startswith("-") for v in self._mapping_arg_match.values())
            and self._mapping_regex_match
        ):  # inline validation for underscore
            raise ValueError("ArgumentMatch's pattern can't start with '-' in this case!")

        self._regex_pattern = "".join(match_pattern_list)
        self._regex = re.compile(self._regex_pattern)

        # ----
        # checking matches
        # ----

        self._list_check_match: List[Tuple[RegexMatch, int]] = []

        group_cnt = 0

        for check_match in check:
            if not isinstance(check_match, RegexMatch):
                raise ValueError(f"{check_match} can't be used as checking match!")
            self._list_check_match.append((check_match, group_cnt + 1))
            group_cnt += re.compile(check_match.gen_regex()).groups
        self._check_pattern: str = "".join(check_match.gen_regex() for check_match in check)
        self._check_regex = re.compile(self._check_pattern)

    # ---
    # Runtime populate
    # ---

    def populate_check_match(self, string: str, elem_mapping: Dict[int, Element]) -> List[str]:
        if not self._check_pattern:
            return split(string)
        if regex_match := self._check_regex.match(string):
            for match, index in self._list_check_match:
                current = regex_match.group(index) or ""
                if isinstance(match, ElementMatch):
                    if current:
                        index = re.fullmatch("\x02(\\d+)_\\w+\x03", current).group(1)
                        result = elem_mapping[int(index)]
                    else:
                        result = None
                else:
                    result = MessageChain.fromMappingString(current, elem_mapping)

                match.result = result
                match.matched = bool(current)

                if match.__class__ is RegexMatch:
                    match.regex_match = re.fullmatch(match.pattern, current)
            return split(string[regex_match.end() :])
        else:
            raise ValueError(f"Not matching regex: {self._check_pattern}")

    def populate_arg_match(self, args: List[str]) -> List[str]:
        if not self._parser_ref:  # Optimization: skip if no ArgumentMatch
            return args
        namespace, rest = self._parser.parse_known_args(args)
        for arg_name, match in self._parser_ref.items():
            namespace_val = getattr(namespace, arg_name, ...)
            if namespace_val is not ...:
                match.result = namespace_val
                match.matched = bool(namespace_val)

        return rest

    def populate_regex_match(self, elem_mapping: Dict[str, Element], arg_list: List[str]) -> None:
        if self._regex_pattern:
            if regex_match := self._regex.fullmatch(" ".join(arg_list)):
                for _, (match, index) in self._mapping_regex_match.items():
                    current = regex_match.group(index) or ""
                    if isinstance(match, ElementMatch):
                        if current:
                            index = re.fullmatch("\x02(\\d+)_\\w+\x03", current).group(1)
                            result = elem_mapping[int(index)]
                        else:
                            result = None
                    else:
                        result = MessageChain.fromMappingString(current, elem_mapping)

                    match.result = result
                    match.matched = bool(current)

                    if match.__class__ is RegexMatch:
                        match.regex_match = re.fullmatch(match.pattern, current)

            else:
                raise ValueError(f"Regex not matching: {self._regex_pattern}")

    def get_help(self, description: str = "", epilog: str = "", *, header: bool = True) -> str:

        formatter = self._parser._get_formatter()

        description = description or self._description
        formatter.add_text(description)

        if header:
            header: List[str] = ["使用方法:"]

            for match, *_ in self._list_check_match:
                header.append(match.get_help())

            for match, *_ in self._mapping_regex_match.values():
                header.append(match.get_help())

            formatter.add_usage(None, self._parser._actions, [], prefix=" ".join(header) + " ")

        positional, optional, *_ = self._parser._action_groups
        formatter.start_section("位置匹配")
        for name, (match, _) in self._mapping_regex_match.items():
            formatter.add_text(f"{name} -> 匹配 {match.get_help()}{' : ' + match.help if match.help else ''}")
        formatter.add_arguments(positional._group_actions)
        formatter.end_section()

        formatter.start_section("参数匹配")
        formatter.add_arguments(optional._group_actions)
        formatter.end_section()

        epilog = epilog or self._epilog
        formatter.add_text(epilog)

        # determine help from format above
        return formatter.format_help()


T_Sparkle = TypeVar("T_Sparkle", bound=Sparkle)


class _TwilightLocalStorage(TypedDict):
    result: Optional[Sparkle]


class Twilight(BaseDispatcher, Generic[T_Sparkle]):
    """
    暮光.
    """

    @overload
    def __init__(self, root: Dict[str, Match], *, map_params: Optional[Dict[str, bool]] = None):
        """本魔法方法用于初始化本实例.

        Args:
            check (Dict[str, Match]): 匹配的映射.
            map_params (Dict[str, bool], optional): 向 MessageChain.asMappingString 传入的参数.
        """

    @overload
    def __init__(
        self, root: Union[Type[T_Sparkle], T_Sparkle], *, map_params: Optional[Dict[str, bool]] = None
    ):
        """本魔法方法用于初始化本实例.

        Args:
            root (Union[Type[Twilight], Twilight], optional): 根 Sparkle 实例, 用于生成新的 Sparkle.
            map_params (Dict[str, bool], optional): 向 MessageChain.asMappingString 传入的参数.
        """

    @overload
    def __init__(
        self,
        root: Iterable[RegexMatch],
        match: Dict[str, Match] = ...,
        *,
        map_params: Optional[Dict[str, bool]] = None,
    ):
        """本魔法方法用于初始化本实例.

        Args:
            check (Iterable[RegexMatch]): 用于检查的 Match 对象.
            match (Dict[str, Match]): 额外匹配的映射.
            map_params (Dict[str, bool], optional): 向 MessageChain.asMappingString 传入的参数.
        """

    def __init__(self, root=..., match=..., *, map_params: Optional[Dict[str, bool]] = None):
        """Actual implementation of __init__"""
        if isinstance(root, Sparkle):
            self.root = root
        elif isinstance(root, type) and issubclass(root, Sparkle):
            self.root = root()
        else:
            self.root = Sparkle(check=root, match=match)

        self._map_params = map_params or {}

    def generate(self, chain: MessageChain) -> T_Sparkle:
        sparkle = deepcopy(self.root)
        mapping_str, elem_mapping = chain.asMappingString(**self._map_params)
        token = elem_mapping_ctx.set(chain)
        try:
            str_list = sparkle.populate_check_match(mapping_str, elem_mapping)
            arg_list = sparkle.populate_arg_match(str_list)
            sparkle.populate_regex_match(elem_mapping, arg_list)
        except Exception:
            raise
        elem_mapping_ctx.reset(token)
        return sparkle

    async def beforeExecution(self, interface: DispatcherInterface):
        local_storage: _TwilightLocalStorage = interface.execution_contexts[-1].local_storage
        chain: MessageChain = await interface.lookup_param("message_chain", MessageChain, None, [])
        try:
            local_storage["result"] = self.generate(chain)
        except Exception:
            raise ExecutionStop

    async def catch(self, interface: DispatcherInterface) -> Optional[Union["Twilight", T_Sparkle, Match]]:
        local_storage: _TwilightLocalStorage = interface.execution_contexts[-1].local_storage
        sparkle = local_storage["result"]
        if issubclass(interface.annotation, Sparkle):
            return sparkle
        if issubclass(interface.annotation, Twilight):
            return self
        if issubclass(interface.annotation, Match):
            return sparkle.get_match(interface.name)
