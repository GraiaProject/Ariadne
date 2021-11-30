import re
import string
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

from ...event.message import MessageEvent
from ..chain import MessageChain
from ..element import Element
from .pattern import (
    ArgumentMatch,
    ElementMatch,
    FullMatch,
    Match,
    RegexMatch,
    WildcardMatch,
)
from .util import ArgumentMatchType, TwilightParser, split


class Sparkle(Representation):
    __dict__: Dict[str, Match]

    @overload
    def __init__(self, check_args: Dict[str, Match]):
        ...

    @overload
    def __init__(
        self,
        check_args: Iterable[Union[FullMatch, RegexMatch]] = (),
        matches: Optional[Dict[str, Match]] = None,
    ):
        ...

    def __init__(
        self,
        check_args: Iterable[Union[FullMatch, RegexMatch]] = (),
        matches: Optional[Dict[str, Match]] = None,
    ):
        if isinstance(check_args, dict):
            matches, check_args = check_args, matches
        match_map = {k: v for k, v in self.__class__.__dict__.items() if isinstance(v, Match)}
        match_map.update(matches if matches else {})

        if any(k.startswith("_") or k[0] in string.digits for k in match_map.keys()):
            raise ValueError("Invalid Match object name!")

        group_cnt: int = 0
        match_pattern_list: List[str] = []

        self._regex_match_list: List[
            Tuple[Union[RegexMatch, FullMatch, WildcardMatch, ElementMatch], int, str]
        ] = []
        self._args_map: Dict[str, Tuple[ArgumentMatch, str]] = {}
        self._parser = TwilightParser(prog="", add_help=False)
        for k, v in match_map.items():
            if isinstance(v, Match):
                if isinstance(v, ArgumentMatch):
                    self._args_map[v.name] = (v, k)
                    if v.action is ... or self._parser.accept_type(v.action):
                        if "type" not in v.add_arg_data or v.add_arg_data["type"] is MessageChain:
                            v.add_arg_data["type"] = ArgumentMatchType(v, v.regex)
                        if isinstance(v.add_arg_data["type"], type) and issubclass(
                            v.add_arg_data["type"], Element
                        ):
                            raise ValueError("Can't use Element as argument type!")
                    self._parser.add_argument(*v.pattern, **v.add_arg_data)
                else:
                    self._regex_match_list.append((v, group_cnt + 1, k))
                    group_cnt += re.compile(v.gen_regex()).groups
                    match_pattern_list.append(v.gen_regex())
        if (
            not all(v[0].pattern[0].startswith("-") for v in self._args_map.values())
            and self._regex_match_list
        ):
            raise ValueError("ArgumentMatch's pattern can't start with '-'!")

        self._regex_pattern = "".join(match_pattern_list)
        self._regex = re.compile(self._regex_pattern)

        self._check_args: List[Tuple[Match, int]] = []

        group_cnt = 0

        for check_match in check_args:
            self._check_args.append((check_match, group_cnt + 1))
            group_cnt += re.compile(check_match.gen_regex()).groups
        self._check_pattern: str = "".join(check_match.gen_regex() for check_match in check_args)
        self._check_regex = re.compile(self._check_pattern)
        self._check_match = None

    def __repr_args__(self):
        check = [(None, [item[0] for item in self._check_args])]
        return check + [(k, v) for k, v in self.__dict__.items() if isinstance(v, Match)]

    def run_check(self, string: str, elem_mapping: Dict[int, Element]) -> List[str]:
        if not self._check_pattern:
            return split(string)
        if regex_match := self._check_regex.match(string):
            for match, index in self._check_args:
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
                    match.regex_match = re.fullmatch(match.pattern, current)
            return split(string[regex_match.end() :])
        else:
            raise ValueError(f"Not matching regex: {self._check_pattern}")

    def parse_arg_list(self, args: List[str]) -> List[str]:
        if not self._args_map:  # Optimization: skip if no ArgumentMatch
            return args
        namespace, rest = self._parser.parse_known_args(args)
        for arg_name, val_tuple in self._args_map.items():
            match, sparkle_name = val_tuple
            namespace_val = getattr(namespace, arg_name, None)
            if arg_name in namespace.__dict__:
                match.result = namespace_val
                match.matched = bool(namespace_val)

            if getattr(self, sparkle_name, None) is None:
                setattr(self, sparkle_name, match)

        return rest

    def match_regex(self, elem_mapping: Dict[str, Element], arg_list: List[str]) -> None:
        if self._regex_pattern:
            if regex_match := self._regex.fullmatch(" ".join(arg_list)):
                for match, index, name in self._regex_match_list:
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
                        match.regex_match = re.fullmatch(match.pattern, current)

                    if getattr(self, name, None) is None:
                        setattr(self, name, match)

            else:
                raise ValueError(f"Regex not matching: {self._regex_pattern}")

    def get_help(
        self,
    ) -> str:
        header: List[str] = ["使用方法:"]

        for match, *_ in self._check_args:
            header.append(match.get_help())

        for match, *_ in self._regex_match_list:
            header.append(match.get_help())

        formatter = self._parser._get_formatter()

        formatter.add_usage(None, self._parser._actions, [], prefix=" ".join(header) + " ")

        positional, optional, *_ = self._parser._action_groups
        formatter.start_section("位置匹配")
        for match, _, name in self._regex_match_list:
            formatter.add_text(f"{name} -> 匹配 {match.get_help()}{' : ' + match.help if match.help else ''}")
        formatter.add_arguments(positional._group_actions)
        formatter.end_section()

        formatter.start_section("参数匹配")
        formatter.add_arguments(optional._group_actions)
        formatter.end_section()

        # determine help from format above
        return formatter.format_help()

    def __getitem__(self, item: Union[str, int]) -> Match:
        if isinstance(item, str):
            return getattr(self, item)
        else:
            return self._check_args[item][0]


T_Sparkle = TypeVar("T_Sparkle", bound=Sparkle)


class _TwilightLocalStorage(TypedDict):
    sparkle: Optional[Sparkle]


class Twilight(BaseDispatcher, Generic[T_Sparkle]):
    """
    暮光.
    """

    def __init__(
        self,
        sparkle: Union[Type[T_Sparkle], T_Sparkle],
        remove_source: bool = True,
        remove_quote: bool = True,
        remove_extra_space: bool = False,
    ):
        """本魔法方法用于初始化本实例.

        Args:
            sparkle (Optional[Type[T_Sparkle]], optional): Sparkle 的子类, 用于生成 Sparkle.
            remove_source (bool, optional): 是否移除消息链中的 Source 元素. 默认为 True.
            remove_quote (bool, optional): 处理时是否要移除消息链的 Quote 元素. 默认为 True.
            remove_extra_space (bool, optional): 是否移除 Quote At AtAll 的多余空格. 默认为 False.
        """
        if isinstance(sparkle, Sparkle):
            self.sparkle_root = sparkle
        else:
            self.sparkle_root = sparkle()
        self.map_params = {
            "remove_source": remove_source,
            "remove_quote": remove_quote,
            "remove_extra_space": remove_extra_space,
        }

    def gen_sparkle(self, chain: MessageChain) -> T_Sparkle:
        sparkle = deepcopy(self.sparkle_root)
        mapping_str, elem_mapping = chain.asMappingString(**self.map_params)
        token = ArgumentMatch.elem_mapping_ctx.set(chain)
        try:
            str_list = sparkle.run_check(mapping_str, elem_mapping)
            arg_list = sparkle.parse_arg_list(str_list)
        except Exception:
            raise
        else:
            sparkle.match_regex(elem_mapping, arg_list)
        ArgumentMatch.elem_mapping_ctx.reset(token)
        return sparkle

    def beforeExecution(self, interface: "DispatcherInterface[MessageEvent]"):
        if not isinstance(interface.event, MessageEvent):
            raise ExecutionStop
        local_storage: _TwilightLocalStorage = interface.broadcast.decorator_interface.local_storage
        chain: MessageChain = interface.event.messageChain
        try:
            local_storage["sparkle"] = self.gen_sparkle(chain)
        except:
            raise ExecutionStop

    async def catch(self, interface: "DispatcherInterface[MessageEvent]") -> Optional[T_Sparkle]:
        local_storage: _TwilightLocalStorage = interface.broadcast.decorator_interface.local_storage
        sparkle = local_storage["sparkle"]
        if issubclass(interface.annotation, Sparkle):
            return sparkle
        if issubclass(interface.annotation, Twilight):
            return self
        if issubclass(interface.annotation, Match):
            if hasattr(sparkle, interface.name):
                match: Match = getattr(sparkle, interface.name)
                if isinstance(match, interface.annotation):
                    return match
