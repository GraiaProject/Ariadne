"""Twilight: 混合式消息链处理器"""
import abc
import enum
import re
from argparse import Action
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Type,
    TypedDict,
    TypeVar,
    Union,
    final,
    overload,
)

from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.decorator import DecoratorInterface
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from pydantic.utils import Representation
from typing_extensions import Self

from graia.ariadne.typing import T
from graia.ariadne.util import get_cls

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
    """禁止尾随空格"""

    PRESERVE = "( )?"
    """预留尾随空格"""

    FORCE = "( )"
    """强制尾随空格"""


NOSPACE = SpacePolicy.NOSPACE
PRESERVE = SpacePolicy.PRESERVE
FORCE = SpacePolicy.FORCE


# ANCHOR: Match


class Match(abc.ABC, Representation):
    """匹配项抽象基类"""

    dest: str

    def __init__(self) -> None:
        self._help = ""
        self.dest = ""

    def help(self, value: str) -> Self:
        """设置匹配项的帮助信息."""
        self._help = value
        return self

    def param(self, target: str) -> Self:
        """设置匹配项的分派位置."""
        self.dest = target
        return self

    def __matmul__(self, other: str) -> Self:
        self.dest = other
        return self

    def __rmatmul__(self, other: str) -> Self:
        self.dest = other
        return self


T_Match = TypeVar("T_Match", bound=Match)


class MatchResult(Generic[T, T_Match], Representation):
    """匹配结果"""

    __slots__ = ("matched", "result", "origin")
    matched: bool
    result: Optional[T]
    origin: T_Match

    def __init__(self, matched: bool, origin: T_Match, result: T = None) -> None:
        self.matched = matched
        self.origin = origin
        self.result = result


T_Result = TypeVar("T_Result", bound=MatchResult)


class RegexMatch(Match):
    """正则表达式匹配"""

    def __init__(self, pattern: str = "", optional: bool = False) -> None:
        super().__init__()
        self.pattern: str = pattern
        self._flags: re.RegexFlag = re.RegexFlag(0)
        self.optional: bool = optional
        self.space_policy: SpacePolicy = SpacePolicy.PRESERVE

    def flags(self, flags: re.RegexFlag) -> Self:
        """设置正则表达式的标志."""
        self._flags = flags
        return self

    def space(self, space: SpacePolicy) -> Self:
        """设置正则表达式的尾随空格策略."""
        self.space_policy = space
        return self

    @final
    @property
    def _regex_str(self) -> str:
        """生成 RegexMatch 相应的正则表达式."""
        return (
            f"{transform_regex(self._flags, self._src)}"
            f"{'?' if self.optional else ''}{self.space_policy.value}"
        )

    @property
    def _src(self) -> str:
        """正则表达式的来源"""
        return self.pattern

    def __repr_args__(self):
        return [(None, self.pattern), ("space", self.space_policy.name), ("flags", self._flags)]


T_RegexMatch = TypeVar("T_RegexMatch", bound=RegexMatch)


class FullMatch(RegexMatch):
    """全匹配"""

    @property
    def _src(self) -> str:
        return re.escape(self.pattern)


class UnionMatch(RegexMatch):
    """多重匹配"""

    pattern: List[str]

    def __init__(
        self,
        *pattern: str,
        optional: bool = False,
    ) -> None:
        super().__init__("", optional)
        self.pattern: List[str] = list(pattern)
        self.optional = optional

    @property
    def _src(self) -> str:
        return f"{'|'.join(re.escape(i) for i in self.pattern)}"


class ElementMatch(RegexMatch):
    """元素类型匹配"""

    type: Type[Element]
    result: Element

    def __init__(
        self,
        type: Type[Element] = ...,
        optional: bool = False,
    ) -> None:
        super(RegexMatch, self).__init__()
        self.type = type
        self.optional = optional
        self._flags: re.RegexFlag = re.RegexFlag(0)
        self.space_policy: SpacePolicy = SpacePolicy.PRESERVE

    @property
    def _src(self) -> str:
        return f"\x02\\d+_{self.type.__fields__['type'].default}\x03"

    def __repr_args__(self):
        return [(None, self.type), ("space", self.space_policy.name), ("flags", self._flags)]


class ParamMatch(RegexMatch):
    """与 WildcardMatch 类似, 但需要至少一个字符. 且仅匹配用空格分开的一段"""

    def __init__(self, optional: bool = False) -> None:
        super().__init__(
            r"""(?:").+?(?:")|(?:').+?(?:')|[^ "']+""",
            optional,
        )

    def __repr_args__(self):
        return [(None, "PARAM"), ("space", self.space_policy.name), ("flags", self._flags)]


class WildcardMatch(RegexMatch):
    """泛匹配"""

    def __init__(self, greed: bool = True, optional: bool = False) -> None:
        super().__init__(f".*{'' if greed else'?'}", optional)


class ArgumentMatch(Match, Generic[T]):
    """参数匹配"""

    @overload
    def __init__(
        self,
        *pattern: str,
        action: Union[str, Type[Action]] = ...,
        nargs: Union[int, str] = ...,
        const: Any = ...,
        default: Any = ...,
        type: Callable[[str], T] = ...,
        choices: Iterable[T] = ...,
        optional: bool = True,
    ):
        ...

    @overload
    def __init__(
        self,
        *pattern: str,
        action: Union[str, Type[Action]] = ...,
        nargs: Union[int, str] = ...,
        const: T = ...,
        default: T = ...,
        type: Callable[[str], T] = ...,
        choices: Iterable[T] = ...,
        optional: bool = True,
    ):
        ...

    def __init__(self, *pattern, **kwargs) -> None:
        super().__init__()
        if not pattern:
            raise ValueError("pattern must not be empty")
        if not all(i.startswith("-") for i in pattern):
            raise ValueError("pattern must start with '-'")
        self.pattern: List[str] = list(pattern)
        self.arg_data: Dict[str, Any] = {}
        for k, v in kwargs.items():
            if k == "optional":
                self.arg_data["required"] = not v
            elif k == "type":
                if v is MessageChain:
                    v = MessageChainType()
                elif isinstance(v, Type) and issubclass(v, Element):
                    v = ElementType(v)
                self.arg_data["type"] = v
            else:
                self.arg_data[k] = v

        if "type" not in self.arg_data:
            self.arg_data["type"] = MessageChainType()

    def param(self, target: str) -> Self:
        self.arg_data["dest"] = target
        return super().param(target)

    def __repr_args__(self):
        return [(None, self.pattern)]


class ArgResult(Generic[T], MatchResult[T, ArgumentMatch]):
    """表示 ArgumentMatch 匹配结果"""

    ...


class RegexResult(MatchResult[MessageChain, RegexMatch]):
    """表示 RegexMatch 匹配结果"""

    ...


class Sparkle(Representation):
    """Sparkle: Twilight 的匹配容器"""

    __slots__ = ("res",)

    def __init__(self, match_result: Dict[str, MatchResult]):
        self.res = match_result

    def __getitem__(self, item: str) -> MatchResult:
        return self.get(item)

    def get(self, item: str) -> MatchResult:
        return self.res[item]

    def __repr_args__(self):
        return [(k, v) for k, v in self.res.items()]


T_Sparkle = TypeVar("T_Sparkle", bound=Sparkle)


class TwilightMatcher:
    """Twilight 匹配器"""

    def __init__(self, *root: Union[Iterable[Match], Match]):
        self._parser = TwilightParser(prog="", add_help=False)
        self._dest_map: Dict[str, ArgumentMatch] = {}
        self._group_map: Dict[int, RegexMatch] = {}
        self.dispatch_ref: Dict[str, Match] = {}
        self.match_ref: DefaultDict[Type[Match], List[Match]] = DefaultDict(list)

        regex_str_list: List[str] = []
        regex_group_cnt: int = 0

        for i in root:
            if isinstance(i, Match):
                i = [i]
            for m in i:
                self.match_ref[type(m)].append(m)
                if isinstance(m, RegexMatch):
                    if m.dest:
                        self._group_map[regex_group_cnt + 1] = m
                    regex_str_list.append(m._regex_str)
                    regex_group_cnt += re.compile(m._regex_str).groups

                elif isinstance(m, ArgumentMatch):
                    if "action" in m.arg_data and "type" in m.arg_data:
                        if not self._parser.accept_type(m.arg_data["action"]):
                            del m.arg_data["type"]
                    action = self._parser.add_argument(*m.pattern, **m.arg_data)
                    if m.dest:
                        self._dest_map[action.dest] = m

                if m.dest:
                    if m.dest in self.dispatch_ref:
                        raise NameError(f"duplicate dispatch name: {m.dest}")
                    self.dispatch_ref[m.dest] = m

        self._regex_pattern: re.Pattern = re.compile("".join(regex_str_list))

    def match(self, arguments: List[str], elem_mapping: Dict[str, Element]) -> Dict[str, MatchResult]:
        """匹配参数
        Args:
            arguments (List[str]): 参数列表
            elem_mapping (Dict[str, Element]): 元素映射

        Returns:
            Dict[str, MatchResult]: 匹配结果
        """
        result: Dict[str, MatchResult] = {}
        if self._dest_map:
            namespace, arguments = self._parser.parse_known_args(arguments)
            nbsp_dict: Dict[str, Any] = namespace.__dict__
            for k, v in self._dest_map.items():
                result[v.dest] = MatchResult(k in nbsp_dict, v, nbsp_dict[k])
        if total_match := self._regex_pattern.fullmatch(" ".join(arguments)):
            for index, match in self._group_map.items():
                group: Optional[str] = total_match.group(index)
                if group is not None:
                    if isinstance(match, ElementMatch):
                        res = elem_mapping[group[1:-1].split("_")[0]]
                    else:
                        res = MessageChain._from_mapping_string(group, elem_mapping)
                else:
                    res = None
                if match.dest:
                    result[match.dest] = MatchResult(group is not None, match, res)
        else:
            raise ValueError(f"{' '.join(arguments)} not matching {self._regex_pattern.pattern}")
        return result

    def get_help(
        self,
        usage: str = "",
        description: str = "",
        epilog: str = "",
    ) -> str:
        """利用 Match 中的信息生成帮助字符串.

        Args:
            usage (str, optional): 使用方法 (命令格式).
            description (str, optional): 前导描述. Defaults to "".
            epilog (str, optional): 后置总结. Defaults to "".

        Returns:
            str: 生成的帮助字符串, 被格式化与缩进过了
        """

        formatter = self._parser._get_formatter()

        formatter.add_text(description)

        if usage:
            formatter.add_usage(None, self._parser._actions, [], prefix=usage + " ")

        _, optional, *_ = self._parser._action_groups

        if self._dest_map:
            formatter.start_section("可选参数")
            formatter.add_arguments(optional._group_actions)
            formatter.end_section()

        formatter.add_text(epilog)

        # determine help from format above
        return formatter.format_help()

    def __repr__(self) -> str:
        return f"<Matcher {list(self._group_map.values()) + list(self._dest_map.values())!r}>"  # type: ignore

    def __str__(self) -> str:
        return repr(list(self._group_map.values()) + list(self._dest_map.values()))  # type: ignore


class _TwilightLocalStorage(TypedDict):
    result: Sparkle


class Twilight(Generic[T_Sparkle], BaseDispatcher):
    """暮光"""

    def __init__(
        self,
        *root: Union[Iterable[Match], Match],
        map_param: Optional[Dict[str, bool]] = None,
    ) -> None:
        """本魔法方法用于初始化本实例.

        Args:
            *root (Iterable[Match] | Match): 匹配规则.
            map_param (Dict[str, bool], optional): 向 MessageChain.asMappingString 传入的参数.
        """
        self.map_param = map_param or {}
        self.matcher: TwilightMatcher = TwilightMatcher(*root)

    def __repr__(self) -> str:
        return f"<Twilight: {self.matcher}>"

    def generate(self, chain: MessageChain) -> T_Sparkle:
        """从消息链生成 Sparkle 实例.

        Args:
            chain (MessageChain): 传入的消息链.

        Returns:
            T_Sparkle: 生成的 Sparkle 对象.
        """
        mapping_str, elem_mapping = chain._to_mapping_str(**self.map_param)
        token = elem_mapping_ctx.set(elem_mapping)
        arguments: List[str] = split(mapping_str, keep_quote=True)
        res = self.matcher.match(arguments, elem_mapping)
        elem_mapping_ctx.reset(token)
        return Sparkle(res)  # type: ignore

    @classmethod
    def from_command(  # ANCHOR: Sparkle: From command
        cls,
        command: str,
        extra_args: Optional[List[Match]] = None,
    ) -> "Twilight":
        """从 shell 式命令生成 Twilight.

        Args:
            command (str): 命令, 使用 {param} 的形式创建参数占位符. 使用 [a|b] 创建选择匹配. 使用 反斜杠 转义.

            extra_args (List[Match], optional): 可选的额外 Match 列表.

        Returns:
            Twilight: 生成的 Twilight.
        """
        extra_args = extra_args or {}
        match: List[RegexMatch] = []

        for t_type, token_list in tokenize_command(command):
            if t_type is CommandToken.TEXT:
                match.append(FullMatch(*token_list).space(SpacePolicy.FORCE))
            elif t_type is CommandToken.CHOICE:
                match.append(UnionMatch(*token_list).space(SpacePolicy.FORCE))
            elif t_type is CommandToken.PARAM:
                match.append(ParamMatch().space(SpacePolicy.FORCE).param(token_list[0]))
            else:
                raise ValueError(f"unexpected token type: {t_type}")

        if match:
            match[-1].space_policy = SpacePolicy.NOSPACE

        if isinstance(extra_args, dict):
            return cls(match, extra_args)
        return cls(match + extra_args)

    def get_help(self, usage: str = "", description: str = "", epilog: str = "") -> str:
        """利用 Match 中的信息生成帮助字符串.

        Args:
            usage (str, optional): 使用方法 (命令格式).
            description (str, optional): 前导描述. Defaults to "".
            epilog (str, optional): 后置总结. Defaults to "".

        Returns:
            str: 生成的帮助字符串, 被格式化与缩进过了
        """
        return self.matcher.get_help(usage, description, epilog)

    async def beforeExecution(self, interface: DispatcherInterface):
        """检验 MessageChain 并将 Sparkle 存入本地存储

        Args:
            interface (DispatcherInterface): DispatcherInterface, 应该能从中提取 MessageChain

        Raises:
            ExecutionStop: 匹配以任意方式失败
        """
        local_storage: _TwilightLocalStorage = interface.local_storage  # type: ignore
        chain: MessageChain = await interface.lookup_param("message_chain", MessageChain, None)
        try:
            local_storage["result"] = self.generate(chain)
        except Exception as e:
            raise ExecutionStop from e

    async def catch(self, interface: DispatcherInterface):
        local_storage: _TwilightLocalStorage = interface.local_storage  # type: ignore
        sparkle = local_storage["result"]
        if issubclass(interface.annotation, Sparkle):
            return sparkle
        if issubclass(interface.annotation, Twilight):
            return self
        if interface.name in sparkle.res:
            result = sparkle.get(interface.name)
            if isinstance(result.origin, interface.annotation):
                return result.origin
            if get_cls(interface.annotation) in {MatchResult, RegexResult, ArgResult}:
                return result
            if isinstance(result.result, interface.annotation):
                return result.result


class ResultValue(Decorator):
    """返回 Match 结果值的装饰器"""

    pre = True

    async def target(i: DecoratorInterface):
        sparkle: Sparkle = i.local_storage["result"]
        if i.name in sparkle.res:
            return sparkle.res[i.name].result
