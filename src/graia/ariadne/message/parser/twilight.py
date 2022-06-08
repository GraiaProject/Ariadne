"""Twilight: 混合式消息链处理器"""
import abc
import contextlib
import enum
import inspect
import re
from argparse import Action, HelpFormatter
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    DefaultDict,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Optional,
    Type,
    TypedDict,
    TypeVar,
    Union,
    cast,
    final,
    overload,
)

from graia.broadcast.builtin.derive import DeriveDispatcher
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.decorator import DecoratorInterface
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from pydantic.utils import Representation
from typing_extensions import Self

from ...typing import AnnotatedType, Sentinel, T, generic_isinstance, generic_issubclass
from ...util import gen_subclass
from ..chain import MessageChain
from ..element import Element
from .base import ChainDecorator
from .util import (
    CommandToken,
    ElementType,
    MessageChainType,
    TwilightHelpManager,
    TwilightParser,
    Unmatched,
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

    dest: Union[int, str]

    def __init__(self) -> None:
        self._help = ""
        self.dest = ""

    def help(self, value: str) -> Self:
        """设置匹配项的帮助信息."""
        self._help = value
        return self

    def param(self, target: Union[int, str]) -> Self:
        """设置匹配项的分派位置."""
        self.dest = target
        return self

    def __matmul__(self, other: Union[int, str]) -> Self:
        return self.param(other)

    def __rmatmul__(self, other: Union[int, str]) -> Self:
        return self.param(other)

    def __rshift__(self, other: Union[int, str]) -> Self:
        return self.param(other)

    def __rlshift__(self, other: Union[int, str]) -> Self:
        return self.param(other)


T_Match = TypeVar("T_Match", bound=Match)


class MatchResult(Generic[T, T_Match], Representation):
    """匹配结果"""

    __slots__ = ("matched", "result", "origin")

    matched: bool
    """是否匹配成功"""

    result: Optional[T]
    """匹配结果"""

    origin: T_Match
    """原来的 Match 对象"""

    def __init__(self, matched: bool, origin: T_Match, result: T = None) -> None:
        """初始化 MatchResult 对象.

        Args:
            matched (bool): 是否匹配成功
            origin (T_Match): 原来的 Match 对象
            result (T, optional): 匹配结果. Defaults to None.
        """
        self.matched = matched
        self.origin = origin
        self.result = result


T_Result = TypeVar("T_Result", bound=MatchResult)


class RegexMatch(Match):
    """正则表达式匹配"""

    pattern: str
    """正则表达式字符串"""

    def __init__(self, pattern: str = "", optional: bool = False) -> None:
        """初始化 RegexMatch 对象.

        Args:
            pattern (str, optional): 正则表达式字符串. Defaults to "".
            optional (bool, optional): 是否可选. Defaults to False.
        Returns:
            None: 无返回.
        """
        super().__init__()
        self.pattern: str = pattern
        self._flags: re.RegexFlag = re.RegexFlag(0)
        self.optional: bool = optional
        self.space_policy: SpacePolicy = SpacePolicy.PRESERVE

    def flags(self, flags: re.RegexFlag) -> Self:
        """设置正则表达式的标志.

        Args:
            flags (re.RegexFlag): 正则表达式旗标.

        Returns:
            Self: RegexMatch 自身.
        """
        self._flags = flags
        return self

    def space(self, space: SpacePolicy) -> Self:
        """设置正则表达式的尾随空格策略.

        Args:
            space (SpacePolicy): 尾随空格策略.

        Returns:
            Self: RegexMatch 自身.
        """
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
    """匹配的选择项"""

    def __init__(
        self,
        *pattern: Union[str, Iterable[str]],
        optional: bool = False,
    ) -> None:
        """初始化 UnionMatch 对象.

        Args:
            *pattern (Union[str, Iterable[str]]): 匹配的选择项.
            optional (bool, optional): 匹配是否可选. Defaults to False.
        """
        super().__init__("", optional)
        self.pattern: List[str] = []
        for p in pattern:
            if isinstance(p, str):
                self.pattern.append(p)
            else:
                self.pattern.extend(p)
        self.optional = optional
        self.help(f"在 {self.pattern} 中选择一项")

    @property
    def _src(self) -> str:
        return f"{'|'.join(re.escape(i) for i in self.pattern)}"


class ElementMatch(RegexMatch):
    """元素类型匹配"""

    type: Type[Element]
    """要匹配的元素类型"""

    def __init__(
        self,
        type: Type[Element] = ...,
        optional: bool = False,
    ) -> None:
        """初始化 ElementMatch 对象.

        Args:
            type (Type[Element]): 元素类型.
            optional (bool, optional): 匹配是否可选. Defaults to False.
        """
        super(RegexMatch, self).__init__()
        self.type = type
        self.optional = optional
        self._flags: re.RegexFlag = re.RegexFlag(0)
        self.space_policy: SpacePolicy = SpacePolicy.PRESERVE
        self.help(f"{self.type.__name__} 元素")

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
        self._help = "参数"

    def __repr_args__(self):
        return [(None, "PARAM"), ("space", self.space_policy.name), ("flags", self._flags)]


class WildcardMatch(RegexMatch):
    """泛匹配"""

    def __init__(self, greed: bool = True, optional: bool = False) -> None:
        """初始化 WildcardMatch 对象.

        Args:
            greed (bool, optional): 是否贪婪匹配. Defaults to True.
            optional (bool, optional): 匹配是否可选. Defaults to False.
        """
        super().__init__(f".*{'' if greed else'?'}", optional)


class ArgumentMatch(Match, Generic[T]):
    """参数匹配"""

    if TYPE_CHECKING:

        @overload
        def __init__(  # type: ignore
            self,
            *pattern: str,
            action: Union[str, Type[Action], Literal[Sentinel]] = Sentinel,
            nargs: Union[int, str, Literal[Sentinel]] = Sentinel,
            const: Union[T, Literal[Sentinel]] = Sentinel,
            default: Union[T, Literal[Sentinel]] = Sentinel,
            type: Union[Callable[[str], T], Literal[Sentinel]] = Sentinel,
            choices: Union[Iterable[T], Literal[Sentinel]] = Sentinel,
            optional: bool = True,
        ):
            """初始化 ArgumentMatch 对象.

            Args:
                *pattern (str): 匹配的参数名.
                action (Union[str, Type[Action]], optional): 参数的动作. Defaults to "store".
                nargs (Union[int, str], optional): 参数的个数.
                const (T, optional): 参数的常量值.
                default (T, optional): 参数的默认值.
                type (Callable[[str], T], optional): 参数的类型.
                choices (Iterable[T], optional): 参数的可选值.
                optional (bool, optional): 参数是否可选. Defaults to True.
            Returns:
                None: 无返回
            """
            ...

    def __init__(self, *pattern: str, **kwargs) -> None:
        """初始化 ArgumentMatch 对象.

        Args:
            *pattern (str): 匹配的参数名.
            action (Union[str, Type[Action]], optional): 参数的动作. Defaults to "store".
            nargs (Union[int, str], optional): 参数的个数.
            const (T, optional): 参数的常量值.
            default (T, optional): 参数的默认值.
            type (Callable[[str], T], optional): 参数的类型.
            choices (Iterable[T], optional): 参数的可选值.
            optional (bool, optional): 参数是否可选. Defaults to True.
        Returns:
            None: 无返回
        """
        super().__init__()
        if not pattern:
            raise ValueError("pattern must not be empty")
        if not all(i.startswith("-") for i in pattern):
            raise ValueError("pattern must start with '-'")
        self.pattern: List[str] = list(pattern)
        self.arg_data: Dict[str, Any] = {"default": Unmatched}
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

    def param(self, target: Union[int, str]) -> Self:
        self.arg_data["dest"] = target if isinstance(target, str) else f"_#!{target}!#_"
        return super().param(target)

    def help(self, value: str) -> Self:
        self.arg_data["help"] = value
        return super().help(value)

    def __repr_args__(self):
        return [(None, self.pattern)]


class ArgResult(Generic[T], MatchResult[T, ArgumentMatch]):
    """表示 ArgumentMatch 匹配结果"""

    ...


class RegexResult(MatchResult[MessageChain, RegexMatch]):
    """表示 RegexMatch 匹配结果"""

    ...


class ElementResult(MatchResult[Element, ElementMatch]):
    """表示 ElementMatch 匹配结果"""

    ...


class ForceResult(MatchResult[T, Match]):
    result: T
    matched: Literal[True]
    ...


class Sparkle(Representation):
    """Sparkle: Twilight 的匹配容器"""

    __slots__ = ("res",)

    def __init__(self, match_result: Dict[Union[int, str], MatchResult]):
        self.res = match_result

    @overload
    def __getitem__(self, item: Union[int, str]) -> MatchResult:
        ...

    @overload
    def __getitem__(self, item: Type[int]) -> List[MatchResult]:
        ...

    @overload
    def __getitem__(self, item: Type[str]) -> Dict[str, MatchResult]:
        ...

    def __getitem__(self, item: Union[int, str, Type[int], Type[str]]):
        if not isinstance(item, type):
            return self.get(item)
        if item is int:
            return [v for k, v in self.res.items() if isinstance(k, int)]
        elif item is str:
            return {k: v for k, v in self.res.items() if isinstance(k, str)}

    def get(self, item: Union[int, str]) -> MatchResult:
        return self.res[item]

    def __repr_args__(self):
        return [(repr(k), v) for k, v in self.res.items()]


T_Sparkle = TypeVar("T_Sparkle", bound=Sparkle)


class TwilightMatcher:
    """Twilight 匹配器"""

    def __init__(self, *root: Union[Iterable[Match], Match]):
        self.origin_match_list: List[Match] = []
        self._parser = TwilightParser(prog="", add_help=False)
        self._dest_map: Dict[str, ArgumentMatch] = {}
        self._group_map: Dict[int, RegexMatch] = {}
        self.dispatch_ref: Dict[Union[int, str], Match] = {}
        self.match_ref: DefaultDict[Type[Match], List[Match]] = DefaultDict(list)

        regex_str_list: List[str] = []
        regex_group_cnt: int = 0

        for i in root:
            if isinstance(i, Match):
                i = [i]
            self.origin_match_list.extend(i)
            for m in i:
                if isinstance(m, RegexMatch):
                    self.match_ref[RegexMatch].append(m)
                    if m.dest:
                        self._group_map[regex_group_cnt + 1] = m
                    regex_str_list.append(m._regex_str)
                    regex_group_cnt += re.compile(m._regex_str).groups

                elif isinstance(m, ArgumentMatch):
                    self.match_ref[ArgumentMatch].append(m)
                    if (
                        "action" in m.arg_data
                        and "type" in m.arg_data
                        and not self._parser.accept_type(m.arg_data["action"])
                    ):
                        del m.arg_data["type"]
                    action = self._parser.add_argument(*m.pattern, **m.arg_data)
                    if m.dest:
                        self._dest_map[action.dest] = m

                if m.dest:
                    if m.dest in self.dispatch_ref:
                        raise NameError(f"duplicate dispatch name: {m.dest}")
                    self.dispatch_ref[m.dest] = m

        self._regex_pattern: re.Pattern = re.compile("".join(regex_str_list))

    def match(
        self, arguments: List[str], elem_mapping: Dict[str, Element]
    ) -> Dict[Union[int, str], MatchResult]:
        """匹配参数
        Args:
            arguments (List[str]): 参数列表
            elem_mapping (Dict[str, Element]): 元素映射

        Returns:
            Dict[Union[int, str], MatchResult]: 匹配结果
        """
        result: Dict[Union[int, str], MatchResult] = {}
        if self._dest_map:
            namespace, arguments = self._parser.parse_known_args(arguments)
            nbsp_dict: Dict[str, Any] = namespace.__dict__
            for k, v in self._dest_map.items():
                res = nbsp_dict.get(k, Unmatched)
                result[v.dest] = MatchResult(res is not Unmatched, v, res)
        if not (total_match := self._regex_pattern.fullmatch(" ".join(arguments))):
            raise ValueError(f"{' '.join(arguments)} not matching {self._regex_pattern.pattern}")
        for index, match in self._group_map.items():
            group: Optional[str] = total_match.group(index)
            if group is None:
                res = None
            else:
                res = (
                    elem_mapping[group[1:-1].split("_")[0]]
                    if isinstance(match, ElementMatch)
                    else MessageChain._from_mapping_string(group, elem_mapping)
                )

            if match.dest:
                if isinstance(match, WildcardMatch):
                    result[match.dest] = MatchResult(bool(res), match, res)
                else:
                    result[match.dest] = MatchResult(group is not None, match, res)
        return result

    def get_help(
        self,
        usage: str = "",
        description: str = "",
        epilog: str = "",
        dest: bool = True,
        sep: str = " -> ",
        formatter_class: Type[HelpFormatter] = HelpFormatter,
    ) -> str:
        """利用 Match 中的信息生成帮助字符串.

        Args:
            usage (str, optional): 使用方法 (命令格式).
            description (str, optional): 前导描述. Defaults to "".
            epilog (str, optional): 后置总结. Defaults to "".
            dest (bool, optional): 是否显示分派位置. Defaults to True.
            sep (str, optional): 分派位置分隔符. Defaults to " -> ".
            formatter_class (Type[HelpFormatter], optional): 帮助格式化器. Defaults to HelpFormatter.

        Returns:
            str: 生成的帮助字符串, 被格式化与缩进过了
        """

        formatter = formatter_class(prog="")

        if usage:
            formatter.add_usage(None, self._parser._actions, [], prefix=f"{usage} ")

        formatter.add_text(description)

        _, optional, *_ = self._parser._action_groups

        if self.match_ref[RegexMatch]:
            formatter.start_section("匹配项")
            for match in self.match_ref[RegexMatch]:
                if match._help:
                    formatter.add_text(
                        f"""{ f"{match.dest}{sep}" if dest and match.dest else ""}{match._help}"""
                    )
            formatter.end_section()

        if self.match_ref[ArgumentMatch]:
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


class _TwilightHelpArgs(TypedDict):
    usage: str
    description: str
    epilog: str
    dest: bool
    sep: str
    formatter_class: Type[HelpFormatter]


class Twilight(Generic[T_Sparkle], BaseDispatcher):
    """暮光"""

    preprocessor: Union[ChainDecorator, AnnotatedType, None] = None

    def __init__(
        self,
        *root: Union[Iterable[Match], Match],
        map_param: Optional[Dict[str, bool]] = None,
        preprocessor: Union[ChainDecorator, AnnotatedType, None, Literal[Sentinel]] = Sentinel,
    ) -> None:
        """本魔法方法用于初始化本实例.

        Args:
            *root (Iterable[Match] | Match): 匹配规则.
            map_param (Dict[str, bool], optional): 控制 MessageChain 转化的参数.
            preprocessor (ChainDecorator, optional): 消息链预处理器. \
            应该来自 `graia.ariadne.message.parser.base` 模块. Defaults to None.
        """
        self.map_param = map_param or {}
        if preprocessor is not Sentinel:
            self.preprocessor = preprocessor
        self.help_data: Optional[_TwilightHelpArgs] = None
        self.help_id: str = TwilightHelpManager.AUTO_ID
        self.help_brief: str = TwilightHelpManager.AUTO_ID
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
        return cast(T_Sparkle, Sparkle(res))

    @classmethod
    def from_command(  # ANCHOR: Sparkle: From command
        cls,
        command: str,
        extra_args: Optional[List[Match]] = None,
    ) -> "Twilight":
        """从 shell 式命令生成 Twilight.

        Args:
            command (str): 命令, 使用 {param} 或 {0} 的形式创建参数占位符. 使用 [a|b] 创建选择匹配. 使用 反斜杠 转义.

            extra_args (List[Match], optional): 可选的额外 Match 列表.

        Returns:
            Twilight: 生成的 Twilight.
        """
        extra_args = extra_args or []
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

        return cls(*match, *extra_args)

    def help(
        self,
        usage: str = "",
        description: str = "",
        epilog: str = "",
        dest: bool = True,
        sep: str = " -> ",
        formatter_class: Type[HelpFormatter] = HelpFormatter,
        *,
        brief: Optional[str] = None,
        help_id: str = TwilightHelpManager.AUTO_ID,
        manager: Union[str, TwilightHelpManager] = "global",
    ) -> Self:
        """利用 Match 中的信息生成帮助字符串.

        Args:
            usage (str, optional): 使用方法 (命令格式).
            description (str, optional): 前导描述. Defaults to "".
            epilog (str, optional): 后置总结. Defaults to "".
            dest (bool, optional): 是否显示分派位置. Defaults to True.
            sep (str, optional): 分派位置之间的分隔符. Defaults to " -> ".
            formatter_class (Type[HelpFormatter], optional): 帮助格式化器. Defaults to HelpFormatter.
            help_id (str, optional): 帮助 id. 默认为自动生成 (推荐自行指定).
            brief (str, optional): 简要介绍, 默认与 description 相同.
            manager (str, optional): 帮助信息管理器. 默认 "global" (全局管理器).

        Returns:
            str: 生成的帮助字符串, 被格式化与缩进过了
        """
        self.help_data = {
            "usage": usage,
            "description": description,
            "epilog": epilog,
            "dest": dest,
            "sep": sep,
            "formatter_class": formatter_class,
        }
        self.help_id = help_id
        self.help_brief = brief or description
        help_mgr = TwilightHelpManager.get_help_mgr(manager)
        help_mgr.register(self)
        return self

    def get_help(
        self,
        usage: str = "",
        description: str = "",
        epilog: str = "",
        dest: bool = True,
        sep: str = " -> ",
        formatter_class: Type[HelpFormatter] = HelpFormatter,
    ) -> str:
        """利用 Match 中的信息生成帮助字符串.

        Args:
            usage (str, optional): 使用方法 (命令格式).
            description (str, optional): 前导描述. Defaults to "".
            epilog (str, optional): 后置总结. Defaults to "".
            dest (bool, optional): 是否显示分派位置. Defaults to True.
            sep (str, optional): 分派位置分隔符. Defaults to " -> ".
            formatter_class (Type[HelpFormatter], optional): 帮助格式化器. Defaults to HelpFormatter.

        Returns:
            str: 生成的帮助字符串, 被格式化与缩进过了
        """
        if self.help_data:
            return self.matcher.get_help(**self.help_data)
        return self.matcher.get_help(usage, description, epilog, dest, sep, formatter_class)

    async def beforeExecution(self, interface: DispatcherInterface):
        """检验 MessageChain 并将 Sparkle 存入本地存储

        Args:
            interface (DispatcherInterface): DispatcherInterface, 应该能从中提取 MessageChain

        Raises:
            ExecutionStop: 匹配以任意方式失败
        """
        local_storage = interface.local_storage
        chain: MessageChain
        if isinstance(self.preprocessor, ChainDecorator):
            chain = await interface.lookup_by_directly(
                DecoratorInterface(), "message_chain", MessageChain, self.preprocessor
            )
        elif isinstance(self.preprocessor, AnnotatedType):
            chain = await interface.lookup_by_directly(
                DeriveDispatcher(), "twilight_derive", self.preprocessor, None
            )
        else:
            chain = await interface.lookup_param("message_chain", MessageChain, None)
        with contextlib.suppress(Exception):
            local_storage[f"{__name__}:result"] = self.generate(chain)
            local_storage[f"{__name__}:twilight"] = self
            return
        interface.stop()

    async def catch(self, interface: DispatcherInterface):
        local_storage = interface.local_storage
        sparkle: T_Sparkle = local_storage[f"{__name__}:result"]
        if generic_issubclass(Sparkle, interface.annotation):
            return sparkle
        if generic_issubclass(Twilight, interface.annotation):
            return self
        if interface.name in sparkle.res:
            result = sparkle.get(interface.name)
            if generic_isinstance(result.origin, interface.annotation):
                from loguru import logger

                logger.warning(
                    f"Please use {interface.name}: {result.__class__.__qualname__} to get origin attribute!"
                )
                interface.stop()
            if any(
                generic_issubclass(res_cls, interface.annotation) for res_cls in gen_subclass(MatchResult)
            ):
                return result
            if generic_isinstance(result.result, interface.annotation):
                return result.result


class ResultValue(Decorator):
    """返回 Match 结果值的装饰器"""

    pre = True

    def __call__(self, _: Any, i: DispatcherInterface) -> Any:
        sparkle: Sparkle = i.local_storage[f"{__name__}:result"]
        res = sparkle.res.get(i.name, None)
        if generic_isinstance(res, i.annotation):
            return res
        i.stop()

    @staticmethod
    async def target(i: DecoratorInterface):
        sparkle: Sparkle = i.local_storage[f"{__name__}:result"]
        res = sparkle.res.get(i.name, None)
        if generic_isinstance(res, i.annotation):
            return res
        raise ExecutionStop


class Help(Decorator, Generic[T]):
    """返回帮助信息的装饰器"""

    pre = True

    formatter: Optional[Callable[[str, DecoratorInterface], Union[Awaitable[T], T]]]

    @overload
    def __init__(self) -> None:
        ...

    @overload
    def __init__(self, formatter: Callable[[str, DecoratorInterface], Union[Awaitable[T], T]]) -> None:
        ...

    def __init__(
        self, formatter: Optional[Callable[[str, DecoratorInterface], Union[Awaitable[T], T]]] = None
    ) -> None:
        """
        Args:
            formatter (Optional[Callable[[str, DecoratorInterface], Union[Awaitable[T], T]]], optional): \
                帮助信息格式化函数.
        """
        self.formatter = formatter

    async def target(self, i: DecoratorInterface) -> T:
        twilight: Twilight = i.local_storage[f"{__name__}:twilight"]
        help_string: str = twilight.matcher.get_help(**(twilight.help_data or {}))
        if self.formatter:
            coro_or_result = self.formatter(help_string, i)
            if inspect.isawaitable(coro_or_result):
                return await coro_or_result
            else:
                return cast(T, coro_or_result)
        return cast(T, help_string)
