import re
import string
from copy import deepcopy
from shlex import split
from types import TracebackType
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
)

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from ...event.message import MessageEvent
from ..chain import MessageChain
from ..element import Element
from .pattern import ArgumentMatch, ElementMatch, FullMatch, Match, RegexMatch
from .util import ArgumentMatchType, TwilightParser


class Sparkle:
    __dict__: Dict[str, Match]

    def __init__(
        self,
        check_args: Iterable[Match] = (),
        matches: Optional[Union[Dict[str, Match], Iterable[Tuple[str, Match]]]] = None,
    ):
        if matches is None or isinstance(matches, dict):
            match_map: Dict[str, Match] = matches or {
                k: v for k, v in self.__class__.__dict__.items() if isinstance(v, Match)
            }
        else:
            match_map: Dict[str, Match] = {k: v for k, v in matches}
        match_map = {
            f"_check_{i}": val for i, val in enumerate(check_args)
        } | match_map  # ensure check args come first

        if any(
            k.startswith("_")
            and not re.fullmatch(r"_check_(\d+)", k)
            or k[0] in string.digits
            for k in match_map.keys()
        ):
            raise ValueError("Invalid Match object name!")

        group_cnt: int = 0
        pattern_list: List[str] = []

        self._regex_match_list: List[Tuple[str, Union[RegexMatch, FullMatch], int]] = []
        self._args_map: Dict[str, Tuple[ArgumentMatch, str]] = {}
        self._parser = TwilightParser()
        for k, v in match_map.items():
            if isinstance(v, Match):
                if isinstance(v, ArgumentMatch):
                    self._args_map[v.name] = (v, k)
                    if v.action is not ... and self._parser.accept_type(v.action):
                        v.add_arg_data["type"] = ArgumentMatchType(v, v.regex)
                    self._parser.add_argument(*v.pattern, **v.add_arg_data)
                else:
                    self._regex_match_list.append((k, v, group_cnt + 1))
                    group_cnt += re.compile(v.gen_regex()).groups
                    pattern_list.append(v.gen_regex())

        self._regex_pattern = "".join(pattern_list)
        self._regex = re.compile(self._regex_pattern)

    def __repr__(self) -> str:
        repr_dict: Dict[str, Match] = {
            k: v for k, v in self.__dict__.items() if isinstance(v, Match)
        }
        return f"<Sparkle: {repr_dict}>"

    def parse_arg_list(self, args: List[str]) -> List[str]:
        namespace, rest = self._parser.parse_known_args(args)
        for arg_name, val_tuple in self._args_map.items():
            match, sparkle_name = val_tuple
            namespace_val = getattr(namespace, arg_name, None)
            if arg_name in namespace.__dict__:
                setattr(
                    self,
                    sparkle_name,
                    match.clone(namespace_val, bool(namespace_val)),
                )
        return rest

    def match_regex(
        self, elem_mapping: Dict[str, Element], arg_list: List[str]
    ) -> None:
        if self._regex_pattern:
            if regex_match := self._regex.fullmatch(" ".join(arg_list)):
                for name, match, index in self._regex_match_list:
                    current = regex_match.group(index) or ""
                    if isinstance(match, ElementMatch):
                        if current:
                            index = re.fullmatch("\b(\\d+)_\\w+\b", current).group(1)
                            result = elem_mapping[int(index)]
                        else:
                            result = None
                    else:
                        result = MessageChain.fromMappingString(current, elem_mapping)
                    if isinstance(match, RegexMatch):
                        setattr(  # sparkle.{name} = toMessageChain(current)
                            self,
                            name,
                            match.clone(
                                result=result,
                                matched=bool(current),
                                re_match=re.match(match.pattern, current),
                            ),
                        )
                    else:
                        setattr(
                            self,
                            name,
                            match.clone(
                                result=result,
                                matched=bool(current),
                            ),
                        )
            else:
                raise ValueError(f"Regex not matching: {self._regex_pattern}")


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
        str_list = split(mapping_str)
        try:
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
        local_storage: _TwilightLocalStorage = (
            interface.broadcast.decorator_interface.local_storage
        )
        chain: MessageChain = interface.event.messageChain
        try:
            local_storage["sparkle"] = self.gen_sparkle(chain)
        except:
            raise ExecutionStop

    async def catch(
        self, interface: "DispatcherInterface[MessageEvent]"
    ) -> Optional[T_Sparkle]:
        local_storage: _TwilightLocalStorage = (
            interface.broadcast.decorator_interface.local_storage
        )
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

    def afterExecution(
        self,
        interface: "DispatcherInterface",
        exception: Optional[Exception],
        tb: Optional[TracebackType],
    ):
        if "sparkle" in interface.broadcast.decorator_interface.local_storage:
            del interface.broadcast.decorator_interface.local_storage["sparkle"]
