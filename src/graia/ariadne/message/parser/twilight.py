"""Twilight: 混合式消息链处理器"""
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
    Set,
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
    CommandToken,
    ElementType,
    MessageChainType,
    TwilightParser,
    elem_mapping_ctx,
    split,
    tokenize_command,
    transform_regex,
)


class SpacePolicy(str, enum.Enum):
    """指示 RegexMatch 的尾随空格策略."""

    value: str
    NOSPACE = ""
    PRESERVE = "( )?"
    FORCE = "( )"


NOSPACE = SpacePolicy.NOSPACE
PRESERVE = SpacePolicy.PRESERVE
FORCE = SpacePolicy.FORCE


# ANCHOR: Match


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
        args = []
        if self.matched is not None:
            args.append(("matched", self.matched))
            args.append(("result", self.result))
        args.append(("pattern", self.pattern))
        return args

    def __deepcopy__(self, _):
        return copy(self)


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
        """生成 RegexMatch 相应的正则表达式."""
        return (
            f"{transform_regex(self.flags, self.regex_src)}"
            f"{'?' if self.optional else ''}{self.space.value}"
        )

    @property
    def regex_src(self) -> str:
        """正则表达式的来源"""
        return self.pattern

    def get_help(self) -> str:
        """生成用于 `Sparkle.get_help()` 的描述性字符串."""
        return self.pattern.replace("( )?", " ") if not self.alt_help else self.alt_help

    def __repr_args__(self):
        return super().__repr_args__() + [("space", self.space.name)]


class ParamMatch(RegexMatch):
    """与 WildcardMatch 类似, 但需要至少一个字符. 且仅匹配用空格分开的一段. (不支持输入的转义处理, 但是可以处理不同引号包裹)"""

    def __init__(
        self,
        *tags: Union[str, int],
        optional: bool = False,
        flags: re.RegexFlag = re.RegexFlag(0),
        space: SpacePolicy = SpacePolicy.PRESERVE,
        help: str = "",
        alt_help: str = "",
        preserve_space: bool = ...,
    ) -> None:
        super().__init__(
            r"""(?:").+?(?:")|(?:').+?(?:')|[^ "']+""",
            optional=optional,
            flags=flags,
            space=space,
            help=help,
            alt_help=alt_help,
            preserve_space=preserve_space,
        )
        self.tags: List[Union[int, str]] = list(tags)

    def get_help(self) -> str:
        return "PARAM"

    def __repr_args__(self):
        args = super().__repr_args__()
        args.append(("tags", self.tags))
        args.remove(("pattern", self.pattern))
        return args


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

    pattern: Type[Element]
    result: Element

    def __init__(
        self,
        type: Type[Element] = ...,
        *,
        optional: bool = False,
        flags: re.RegexFlag = re.RegexFlag(0),
        space: SpacePolicy = SpacePolicy.PRESERVE,
        help: str = "",
        alt_help: str = "",
        preserve_space: bool = ...,
    ) -> None:
        super().__init__(
            type,
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
    nargs: Union[str, int]
    action: Union[str, Type[Action]]
    dest: Optional[str]
    choices: Optional[Iterable]
    const: Any
    default: Any
    regex: Optional[re.Pattern]
    result: Union["MessageChain", List, Any]
    add_arg_data: Dict[str, Any]

    def __new__(cls: Type["ArgumentMatch"], *pattern: str, **kwargs):
        if any(not p.startswith("-") for p in pattern):
            import warnings

            warnings.warn("use ParamMatch for positional argument!", DeprecationWarning)
            warnings.warn("This behaviour will be removed in 0.5.2!", DeprecationWarning)
            return ParamMatch(*pattern, **kwargs)
        return super().__new__(cls)

    def __init__(
        self,
        *pattern: str,
        optional: bool = True,
        action: Union[str, Type[Action]] = ...,
        nargs: Union[int, str] = ...,
        const: Any = ...,
        default: Any = ...,
        type: Callable[[str], Any] = ...,
        choices: Iterable = ...,
        help: str = ...,
        dest: str = ...,
        regex: str = ...,
    ) -> None:
        if not pattern:
            raise ValueError("Expected at least 1 pattern!")
        super().__init__(pattern, optional, help if help is not ... else "")
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
            if type is MessageChain:
                type = MessageChainType(self.regex)
            elif isinstance(type, Type) and issubclass(type, Element):
                type = ElementType(type)
            data["type"] = type
        else:
            data["type"] = MessageChainType(self.regex)
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


# ANCHOR: Sparkle
class Sparkle(Representation):
    """Sparkle: Twilight 的匹配容器"""

    __dict__: Dict[str, Match]

    _description: str = ""
    _epilog: str = ""

    def __repr_args__(self):
        check = [(None, [item[0] for item in self._list_check_match])]
        return [
            *check,
            *[(k, v) for k, (v, _) in self._mapping_regex_match.items()],
            *list(self._mapping_arg_match.items()),
        ]

    @overload
    def __getitem__(self, item: Union[str, int]) -> Match:
        ...

    @overload
    def __getitem__(self, item: Type[T_Match]) -> List[T_Match]:
        ...

    @overload
    def __getitem__(self, item: Tuple[Type[T_RMatch], int]) -> T_RMatch:
        ...

    def __getitem__(self, item: Union[str, int, Type[T_Match], Tuple[Type[T_RMatch], int]]):
        return self.get_match(item)

    def __init_subclass__(cls, /, *, description: str = "", epilog: str = "", **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._description = description
        cls._epilog = epilog

    def __getattribute__(self, _name: str):
        obj = super().__getattribute__(_name)
        if isinstance(obj, Match):
            return self.get_match(_name)
        return obj

    @overload
    def get_match(self, item: Union[str, int]) -> Match:
        ...

    @overload
    def get_match(self, item: Type[T_Match]) -> List[T_Match]:
        ...

    @overload
    def get_match(self, item: Tuple[T_RMatch, int]) -> T_RMatch:
        ...

    def get_param(self, tag: Union[int, str]) -> ParamMatch:
        """通过 tag 获取对应的 ParamMatch 实例

        Args:
            tag (Union[int, str]): ParamMatch 的 tag

        Returns:
            ParamMatch: 获取到的 ParamMatch

        """
        return self._param_match_ref[tag]

    def get_match(
        self, item: Union[str, int, Type[T_Match], Tuple[Type[T_RMatch], int]]
    ) -> Union[List[Match], Match]:
        """获取 Match 列表 / 实例.

        Args:
            item (Union[str, int, Type[T_Match], Tuple[Type[T_RMatch], int]]): 提供的信息, 请参见重载.

        Raises:
            KeyError: 找不到 Match.

        Returns:
            Union[List[Match], Match]: 获取的 Match 列表 / 实例.
        """
        if isinstance(item, int):
            return self._list_check_match[item][0]
        if isinstance(item, str):
            if item in self._mapping_arg_match:
                return self._mapping_arg_match[item]
            if item in self._mapping_regex_match:
                return self._mapping_regex_match[item][0]
            if item in self._param_match_ref:
                return self._param_match_ref[item]
        if isinstance(item, type):
            return self._match_ref[item]
        if isinstance(item, tuple):
            typ, ind = item
            return self._match_ref[typ][ind]
        raise KeyError(f"Unable to find match named {item}")

    def __deepcopy__(self, memo):
        copied = copy(self)

        COPY_ATTRS = {
            "_list_check_match",
            "_mapping_arg_match",
            "_mapping_regex_match",
            "_parser_ref",
            "_match_ref",
            "_param_match_ref",
        }

        for attr_name in COPY_ATTRS:
            setattr(copied, attr_name, deepcopy(getattr(self, attr_name), memo))

        return copied

    @overload
    def __init__(
        self,
        check: Dict[str, Match],
        description: str = "",
        epilog: str = "",
    ):
        ...

    @overload
    def __init__(
        self,
        check: Iterable[Union[Match, str]] = (),
        match: Optional[Dict[str, Match]] = None,
        description: str = "",
        epilog: str = "",
    ):
        ...

    def __init__(
        self,
        check=(),
        match=None,
        description: str = "",
        epilog: str = "",
    ):
        self._description = description or self._description
        self._epilog = epilog or self._epilog

        check, match = (match, check) if isinstance(check, dict) else (check, match)

        check = check if check and check is not ... else ()
        match = match if match and match is not ... else ()

        self._match_ref: DefaultDict[Type[T_Match], List[T_Match]] = DefaultDict(list)

        self._mapping_regex_match: Dict[str, Tuple[RegexMatch, int]] = {}
        self._mapping_arg_match: Dict[str, ArgumentMatch] = {}
        self._parser_ref: Dict[str, ArgumentMatch] = {}

        self._parser = TwilightParser(prog="", add_help=False)

        self._param_match_ref: Dict[Union[int, str], ParamMatch] = {}

        # ----
        # checking matches
        # ----

        self._list_check_match: List[Tuple[RegexMatch, int]] = []

        group_cnt: int = 0

        check_pattern_list: List[str] = []

        for v in check:
            if isinstance(v, str):  # Regex string
                v = RegexMatch(v)

            self._match_ref[v.__class__].append(v)
            if isinstance(v, RegexMatch):
                self._list_check_match.append((v, group_cnt + 1))
                check_pattern_list.append(v.gen_regex())
                group_cnt += re.compile(v.gen_regex()).groups

                if isinstance(v, ParamMatch):  # Validate ParamMatch's tags
                    for tag in v.tags:
                        if tag in self._param_match_ref:
                            raise ValueError(f"Duplicated ParamMatch tag with {self._param_match_ref[tag]}")
                        self._param_match_ref[tag] = v

            elif isinstance(v, ArgumentMatch):
                if not self._parser.accept_type(v.action) and "type" in v.add_arg_data:
                    del v.add_arg_data["type"]
                action = self._parser.add_argument(*v.pattern, **v.add_arg_data)
                v.dest = action.dest
                self._parser_ref[v.dest] = v
                continue

        self._check_pattern: str = "".join(check_pattern_list)

        # ----
        # ordinary matches
        # ----

        match_map = {k: v for k, v in self.__class__.__dict__.items() if isinstance(v, Match)}
        match_map.update(match)

        match_pattern_list: List[str] = []

        group_cnt: int = 0

        for k, v in match_map.items():
            if k.startswith("_") or k[0] in string.digits:
                raise ValueError("Invalid Match object name!")

            self._match_ref[v.__class__].append(v)

            if isinstance(v, ArgumentMatch):  # add to self._parser
                self._mapping_arg_match[k] = v
                if not self._parser.accept_type(v.action) and "type" in v.add_arg_data:
                    del v.add_arg_data["type"]
                action = self._parser.add_argument(*v.pattern, **v.add_arg_data)
                v.dest = action.dest
                self._parser_ref[v.dest] = v
                continue

            if isinstance(v, RegexMatch):  # add to self._mapping_regex_match

                self._mapping_regex_match[k] = (v, group_cnt + 1)
                group_cnt += re.compile(v.gen_regex()).groups
                match_pattern_list.append(v.gen_regex())

                if isinstance(v, ParamMatch):  # Validate ParamMatch's tags
                    for tag in v.tags:
                        if tag in self._param_match_ref:
                            raise ValueError(f"Duplicated ParamMatch tag with {self._param_match_ref[tag]}")
                        self._param_match_ref[tag] = v

                continue

            raise ValueError(f"{v} is neither RegexMatch nor ArgumentMatch!")

        # --- validate ArgumentMatch ---

        if match_pattern_list and self._parser_ref:
            for arg_match in self._parser_ref.values():
                if any(not i.startswith("-") for i in arg_match.pattern):
                    raise ValueError(f'{arg_match} has a pattern not starting with "-"')

        self._regex_pattern = "".join(match_pattern_list)

    @classmethod
    def from_command(  # ANCHOR: Sparkle: From command
        cls: "Type[Sparkle]",
        command: str,
        extra_args: Optional[Union[Dict[str, ArgumentMatch], List[ArgumentMatch]]] = None,
        optional_tag: Iterable[Union[int, str]] = (),
    ) -> "Sparkle":
        """从 shell 式命令生成 Sparkle.

        Args:
            command (str): 命令, 使用 {0} 的形式创建参数占位符. 使用 [a|b] 创建选择匹配. 使用 反斜杠 转义.

            extra_args (Dict[str, ArgumentMatch] | List[ArgumentMatch], optional):
            可选的额外 str -> ArgumentMatch 映射 / ArgumentMatch 列表.

            optional (Iterable[int]): 标注为可选的参数 tag 迭代器.

        Returns:
            Sparkle: 生成的 Sparkle.
        """
        extra_args = extra_args or {}
        match: List[RegexMatch] = []
        optional: Set[Union[int, str]] = set(optional_tag)

        for t_type, token_list in tokenize_command(command):
            if t_type is CommandToken.TEXT:
                match.append(FullMatch(*token_list, space=SpacePolicy.FORCE))
            elif t_type is CommandToken.CHOICE:
                match.append(UnionMatch(*token_list, space=SpacePolicy.FORCE))
            elif t_type is CommandToken.PARAM:
                match.append(ParamMatch(*token_list, space=SpacePolicy.FORCE))
                if any(i in optional for i in token_list):
                    match[-1].optional = True
                    if len(match) >= 2:
                        match[-2].space = SpacePolicy.PRESERVE
            else:
                raise ValueError(f"unexpected token type: {t_type}")

        if match:
            match[-1].space = SpacePolicy.NOSPACE

        if isinstance(extra_args, dict):
            return cls(match, extra_args)
        return cls(match + extra_args)

    # ANCHOR: Sparkle runtime populate

    def populate_check_match(self, arg_list: List[str], elem_mapping: Dict[int, Element]) -> List[str]:
        """从传入的 string 与 elem_mapping 填充本实例的 check_match

        Args:
            arg_list (List[str]): 参数列表
            elem_mapping (Dict[int, Element]): 元素映射

        Raises:
            ValueError: check_match 匹配失败

        Returns:
            List[str]: 剩下的字符串参数列表
        """
        if not self._check_pattern:
            return arg_list
        if regex_match := re.match(self._check_pattern, " ".join(arg_list)):
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

                if isinstance(match, RegexMatch):
                    match.regex_match = re.fullmatch(match.regex_src, current)
            return split(" ".join(arg_list)[regex_match.end() :])
        raise ValueError(f"Not matching regex: {self._check_pattern}")

    def populate_arg_match(self, arg_list: List[str]) -> List[str]:
        """从传入的 string 与填充本实例的 ArgumentMatch 对象

        Args:
            arg_list (List[str]): 参数列表

        Returns:
            List[str]: 剩下的字符串参数列表
        """
        if not self._parser_ref:  # Optimization: skip if no ArgumentMatch
            return arg_list
        namespace, rest = self._parser.parse_known_args(arg_list)
        for arg_name, match in self._parser_ref.items():
            namespace_val = getattr(namespace, arg_name, ...)
            if namespace_val is not ...:
                match.result = namespace_val
                match.matched = bool(namespace_val)

        return rest

    def populate_regex_match(self, arg_list: List[str], elem_mapping: Dict[str, Element]) -> None:
        """从传入的 string 与 elem_mapping 填充本实例的 RegexMatch

        Args:
            arg_list (List[str]): 参数列表
            elem_mapping (Dict[int, Element]): 元素映射

        Raises:
            ValueError: 匹配失败
        """
        if self._regex_pattern:
            if regex_match := re.fullmatch(self._regex_pattern, " ".join(arg_list)):
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
        """利用 Match 中的信息生成帮助字符串.

        Args:
            description (str, optional): 前导描述. Defaults to "".
            epilog (str, optional): 后置总结. Defaults to "".
            header (bool, optional): 生成使用方法 (命令总览). Defaults to True.

        Returns:
            str: 生成的帮助字符串, 被格式化与缩进过了
        """

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


# ANCHOR: Twilight
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
        root: Iterable[Union[Match, str]],
        match: Dict[str, Match] = ...,
        *,
        map_params: Optional[Dict[str, bool]] = None,
    ):
        """本魔法方法用于初始化本实例.

        Args:
            check (Iterable[RegexMatch]): 用于检查的 Match 对象.
            match (Iterable[Union[Match, str]]): 额外匹配的映射 / 正则字符串.
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

    @classmethod
    def from_command(
        cls,
        command: str,
        extra_arg_mapping: Optional[Dict[str, ArgumentMatch]] = None,
        *,
        map_params: Optional[Dict[str, bool]] = None,
    ) -> "Twilight":
        """从 shell 式命令生成 Twilight.

        Args:
            command (str): 命令, 使用 {0} 的形式创建参数占位符.
            extra_arg_mapping (Dict[str, ArgumentMatch], optional): 可选的额外 str -> ArgumentMatch 映射.
            map_params (Dict[str, bool], optional): 向 MessageChain.asMappingString 传入的参数.

        Returns:
            Twilight: 生成的 Twilight.
        """
        return cls(Sparkle.from_command(command, extra_arg_mapping), map_params=map_params)

    def generate(self, chain: MessageChain) -> T_Sparkle:
        """从消息链生成 Sparkle 实例.

        Args:
            chain (MessageChain): 传入的消息链.

        Returns:
            T_Sparkle: 生成的 Sparkle 对象.
        """
        sparkle = deepcopy(self.root)
        mapping_str, elem_mapping = chain.asMappingString(**self._map_params)
        token = elem_mapping_ctx.set(chain)
        try:
            rest = split(mapping_str)
            rest = sparkle.populate_arg_match(rest)
            rest = sparkle.populate_check_match(rest, elem_mapping)
            sparkle.populate_regex_match(rest, elem_mapping)
            return sparkle
        finally:
            elem_mapping_ctx.reset(token)

    async def beforeExecution(self, interface: DispatcherInterface):
        """检验 MessageChain 并将 Sparkle 存入本地存储

        Args:
            interface (DispatcherInterface): DispatcherInterface, 应该能从中提取 MessageChain

        Raises:
            ExecutionStop: 匹配以任意方式失败
        """
        local_storage: _TwilightLocalStorage = interface.execution_contexts[-1].local_storage
        chain: MessageChain = await interface.lookup_param("message_chain", MessageChain, None, [])
        try:
            local_storage["result"] = self.generate(chain)
        except Exception as e:
            raise ExecutionStop from e

    async def catch(self, interface: DispatcherInterface) -> Optional[Union["Twilight", T_Sparkle, Match]]:
        local_storage: _TwilightLocalStorage = interface.execution_contexts[-1].local_storage
        sparkle = local_storage["result"]
        if issubclass(interface.annotation, Sparkle):
            return sparkle
        if issubclass(interface.annotation, Twilight):
            return self
        try:
            match = sparkle.get_match(interface.name)
            if issubclass(interface.annotation, Match):
                return match
            if issubclass(interface.annotation, type(match.result)):
                return match.result
        except KeyError:
            pass
