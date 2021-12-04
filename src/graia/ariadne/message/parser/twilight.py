import re
import string
import warnings
from copy import deepcopy
from typing import (
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypedDict,
    TypeVar,
    Union,
    overload,
)

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from pydantic.utils import Representation

from graia.ariadne.util import cast_to, deprecated

from ...event.message import MessageEvent
from ..chain import MessageChain
from ..element import Element
from .pattern import ArgumentMatch, ElementMatch, Match, RegexMatch
from .util import ElementType, MessageChainType, TwilightParser, elem_mapping_ctx, split


class _TwilightLocalStorage(TypedDict):
    result: Optional["Twilight"]


T_Twilight = TypeVar("T_Twilight", bound="Twilight")


class Twilight(BaseDispatcher, Generic[T_Twilight], Representation):
    """
    暮光.
    """

    __dict__: Dict[str, Match]
    _description: str = ""
    _epilog: str = ""

    PRESERVED_NAMES = (
        # ClassVars
        "elem_mapping_ctx",
        "PRESERVED_NAMES",
        # Methods
        "generate",
        "populate",
        "populate_check",
        "populate_arg_match",
        "populate_regex_match",
        "get_help",
        # Dispatcher methods
        "beforeExecution",
        "catch",
        "afterDispatch",
        "afterExecution",
    )

    def __repr_args__(self):
        check = [(None, [item[0] for item in self._list_check_match])]
        return check + [(k, v) for k, v in self.__dict__.items() if isinstance(v, Match)]

    def __getitem__(self, item: Union[str, int]) -> Match:
        if isinstance(item, str) and item not in self.PRESERVED_NAMES:
            return getattr(self, item)
        if isinstance(item, int):
            return self._list_check_match[item][0]

    def __init_subclass__(cls, /, *, description: str = "", epilog: str = "", **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._description = description
        cls._epilog = epilog

    @overload
    def __init__(
        self,
        check: Dict[str, Match],
        *,
        remove_source: bool = True,
        remove_quote: bool = True,
        remove_extra_space: bool = False,
        description: str = "",
        epilog: str = "",
    ):
        """本魔法方法用于初始化本实例.

        Args:
            check (Dict[str, Match]): 匹配的映射.
            remove_source (bool, optional): 是否移除消息链中的 Source 元素. 默认为 True.
            remove_quote (bool, optional): 处理时是否要移除消息链的 Quote 元素. 默认为 True.
            remove_extra_space (bool, optional): 是否移除 Quote At AtAll 的多余空格. 默认为 False.
            description (str, optional): 本 Twilight 的前置描述, 在 `add_help` 中用到.
            epilog (str, optional): 本 Twilight 的后置描述, 在 `add_help` 中用到.
        """

    @overload
    def __init__(
        self,
        check: Union[Type[T_Twilight], T_Twilight],
        *,
        remove_source: bool = True,
        remove_quote: bool = True,
        remove_extra_space: bool = False,
        description: str = "",
        epilog: str = "",
    ):
        """本魔法方法用于初始化本实例.

        Args:
            check (Union[Type[Twilight], Twilight], optional): 根 Twilight 实例, 用于生成新的 Twilight.
            remove_source (bool, optional): 是否移除消息链中的 Source 元素. 默认为 True.
            remove_quote (bool, optional): 处理时是否要移除消息链的 Quote 元素. 默认为 True.
            remove_extra_space (bool, optional): 是否移除 Quote At AtAll 的多余空格. 默认为 False.
            description (str, optional): 本 Twilight 的前置描述, 在 `add_help` 中用到.
            epilog (str, optional): 本 Twilight 的后置描述, 在 `add_help` 中用到.
        """

    @overload
    def __init__(
        self,
        check: Iterable[RegexMatch],
        match: Dict[str, Match],
        *,
        remove_source: bool = True,
        remove_quote: bool = True,
        remove_extra_space: bool = False,
        description: str = "",
        epilog: str = "",
    ):
        """本魔法方法用于初始化本实例.

        Args:
            check (Iterable[RegexMatch]): 用于检查的 Match 对象.
            match (Dict[str, Match]): 额外匹配的映射.
            remove_source (bool, optional): 是否移除消息链中的 Source 元素. 默认为 True.
            remove_quote (bool, optional): 处理时是否要移除消息链的 Quote 元素. 默认为 True.
            remove_extra_space (bool, optional): 是否移除 Quote At AtAll 的多余空格. 默认为 False.
            description (str, optional): 本 Twilight 的前置描述, 在 `add_help` 中用到.
            epilog (str, optional): 本 Twilight 的后置描述, 在 `add_help` 中用到.
        """

    def __init__(
        self,
        check=None,
        match=None,
        *,
        remove_source: bool = True,
        remove_quote: bool = True,
        remove_extra_space: bool = False,
        description: str = "",
        epilog: str = "",
    ):
        "Actual implementation of __init__."
        self._map_params = {
            "remove_source": remove_source,
            "remove_quote": remove_quote,
            "remove_extra_space": remove_extra_space,
        }
        self._description = description or self._description
        self._epilog = epilog or self._epilog

        if isinstance(check, Twilight):
            warnings.warn(DeprecationWarning("This usage can be removed at any time!"))
            self._root = check
            return

        elif isinstance(check, type):
            warnings.warn(DeprecationWarning("This usage can be removed at any time!"))
            check = cast_to(check, Type[Twilight])
            self._root = check()

        else:  # self generate
            self._root = deepcopy(self)
            self.populate(check=check, match=match)
            self._root.populate(check=check, match=match)

    def populate(
        self,
        check: Iterable[RegexMatch] = None,
        match: Optional[Dict[str, Match]] = None,
        cls: Type["Twilight"] = None,
    ):
        if isinstance(check, dict):
            match, check = check, match  # swap
            check: Iterable[RegexMatch]
            match: Dict[str, Match]

        if not check:
            check = ()

        cls = cls or self.__class__

        match_map = {k: v for k, v in cls.__dict__.items() if isinstance(v, Match)}
        match_map.update(match if match else {})

        # ----
        # ordinary matches
        # ----

        group_cnt: int = 0
        match_pattern_list: List[str] = []

        self._list_regex_match: List[Tuple[RegexMatch, int, str]] = []
        self._mapping_arg_match: Dict[str, Tuple[ArgumentMatch, str]] = {}

        self._parser = TwilightParser(prog="", add_help=False)
        for k, v in match_map.items():
            if k.startswith("_") or k[0] in string.digits or k in self.PRESERVED_NAMES:
                raise ValueError("Invalid Match object name!")

            if isinstance(v, Match):
                if isinstance(v, ArgumentMatch):  # add to self._parser
                    self._mapping_arg_match[v.name] = (v, k)
                    if v.action is ... or self._parser.accept_type(v.action):
                        if "type" not in v.add_arg_data or v.add_arg_data["type"] is MessageChain:
                            v.add_arg_data["type"] = MessageChainType(v, v.regex)
                        elif isinstance(v.add_arg_data["type"], type) and issubclass(
                            v.add_arg_data["type"], Element
                        ):
                            v.add_arg_data["type"] = ElementType(v, v.add_arg_data["type"])
                    self._parser.add_argument(*v.pattern, **v.add_arg_data)

                elif isinstance(v, RegexMatch):  # add to self._list_regex_match
                    self._list_regex_match.append((v, group_cnt + 1, k))
                    group_cnt += re.compile(v.gen_regex()).groups
                    match_pattern_list.append(v.gen_regex())

                else:
                    raise ValueError(f"{v} is neither RegexMatch nor ArgumentMatch!")

        if (
            not all(v[0].pattern[0].startswith("-") for v in self._mapping_arg_match.values())
            and self._list_regex_match
        ):  # inline validation for underscore
            raise ValueError("ArgumentMatch's pattern can't start with '-' in this case!")

        self._regex_pattern = "".join(match_pattern_list)
        self._regex = re.compile(self._regex_pattern)

        # ----
        # checking matches
        # ----

        self._list_check_match: List[Tuple[Match, int]] = []

        group_cnt = 0

        for check_match in check:
            if not isinstance(check_match, RegexMatch):
                raise ValueError(f"{check_match} can't be used as checking match!")
            self._list_check_match.append((check_match, group_cnt + 1))
            group_cnt += re.compile(check_match.gen_regex()).groups
        self._check_pattern: str = "".join(check_match.gen_regex() for check_match in check)
        self._check_regex = re.compile(self._check_pattern)

    def generate(self, chain: MessageChain) -> T_Twilight:
        obj = deepcopy(self._root)
        mapping_str, elem_mapping = chain.asMappingString(**self._map_params)
        token = elem_mapping_ctx.set(chain)
        try:
            str_list = obj.populate_check_match(mapping_str, elem_mapping)
            arg_list = obj.populate_arg_match(str_list)
            obj.populate_regex_match(elem_mapping, arg_list)
            return obj
        except Exception:
            raise
        finally:
            elem_mapping_ctx.reset(token)

    @deprecated("0.5.0")
    def gen_sparkle(self, chain: MessageChain) -> T_Twilight:
        return self.generate(chain)

    # ----
    # Dispatcher methods
    # ----

    def beforeExecution(self, interface: "DispatcherInterface[MessageEvent]"):
        if not isinstance(interface.event, MessageEvent):
            raise ExecutionStop
        local_storage: _TwilightLocalStorage = interface.execution_contexts[-1].local_storage
        chain: MessageChain = interface.event.messageChain
        try:
            local_storage["result"] = self.generate(chain)
        except:
            raise ExecutionStop

    async def catch(
        self, interface: "DispatcherInterface[MessageEvent]"
    ) -> Optional[Union[T_Twilight, Match]]:
        local_storage: _TwilightLocalStorage = interface.execution_contexts[-1].local_storage
        result = local_storage["result"]
        if issubclass(interface.annotation, Twilight):
            return result
        if issubclass(interface.annotation, Match):
            if hasattr(result, interface.name):
                match: Match = getattr(result, interface.name)
                if isinstance(match, interface.annotation):
                    return match

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
        if not self._mapping_arg_match:  # Optimization: skip if no ArgumentMatch
            return args
        namespace, rest = self._parser.parse_known_args(args)
        for arg_name, val_tuple in self._mapping_arg_match.items():
            match, sparkle_name = val_tuple
            namespace_val = getattr(namespace, arg_name, None)
            if arg_name in namespace.__dict__:
                match.result = namespace_val
                match.matched = bool(namespace_val)

            if getattr(self, sparkle_name, None) is None:
                setattr(self, sparkle_name, match)

        return rest

    def populate_regex_match(self, elem_mapping: Dict[str, Element], arg_list: List[str]) -> None:
        if self._regex_pattern:
            if regex_match := self._regex.fullmatch(" ".join(arg_list)):
                for match, index, name in self._list_regex_match:
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

                    if getattr(self, name, None) is None:
                        setattr(self, name, match)

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

            for match, *_ in self._list_regex_match:
                header.append(match.get_help())

            formatter.add_usage(None, self._parser._actions, [], prefix=" ".join(header) + " ")

        positional, optional, *_ = self._parser._action_groups
        formatter.start_section("位置匹配")
        for match, _, name in self._list_regex_match:
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


class Sparkle(Twilight):
    @deprecated("0.5.0")
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
