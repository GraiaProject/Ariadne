"""Ariadne 基础的 parser, 包括 DetectPrefix 与 DetectSuffix"""
import abc
import difflib
import fnmatch
import re
import weakref
from collections import defaultdict
from typing import ClassVar, DefaultDict, Dict, Iterable, List, Optional, Tuple, Type, Union
from typing_extensions import get_args

from graia.broadcast.builtin.derive import Derive
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.decorator import DecoratorInterface
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from ...app import Ariadne
from ...event.message import GroupMessage, MessageEvent
from ...typing import Unions, generic_issubclass, get_origin
from ..chain import MessageChain
from ..element import At, Element, Plain


class ChainDecorator(abc.ABC, Decorator, Derive[MessageChain]):
    pre = True

    @abc.abstractmethod
    async def __call__(self, chain: MessageChain, interface: DispatcherInterface) -> Optional[MessageChain]:
        ...

    async def target(self, interface: DecoratorInterface):
        return await self(
            await interface.dispatcher_interface.lookup_param("message_chain", MessageChain, None),
            interface.dispatcher_interface,
        )


class DetectPrefix(ChainDecorator):
    """前缀检测器"""

    def __init__(self, prefix: Union[str, Iterable[str]]) -> None:
        """初始化前缀检测器.

        Args:
            prefix (Union[str, Iterable[str]]): 要匹配的前缀
        """
        self.prefix: List[str] = [prefix] if isinstance(prefix, str) else list(prefix)

    async def __call__(self, chain: MessageChain, _) -> Optional[MessageChain]:
        for prefix in self.prefix:
            if chain.startswith(prefix):
                return chain.removeprefix(prefix).removeprefix(" ")

        raise ExecutionStop


class DetectSuffix(ChainDecorator):
    """后缀检测器"""

    def __init__(self, suffix: Union[str, Iterable[str]]) -> None:
        """初始化后缀检测器.

        Args:
            suffix (Union[str, Iterable[str]]): 要匹配的后缀
        """
        self.suffix: List[str] = [suffix] if isinstance(suffix, str) else list(suffix)

    async def __call__(self, chain: MessageChain, _) -> Optional[MessageChain]:
        for suffix in self.suffix:
            if chain.endswith(suffix):
                return chain.removesuffix(suffix).removesuffix(" ")
        raise ExecutionStop


class MentionMe(ChainDecorator):
    """At 账号或者提到账号群昵称"""

    def __init__(self, name: Union[bool, str] = True) -> None:
        """
        Args:
            name (Union[bool, str]): 是否提取昵称, 如果为 True, 则自动提取昵称, \
            如果为 False 则禁用昵称, 为 str 则将参数作为昵称
        """
        self.name = name

    async def __call__(self, chain: MessageChain, interface: DispatcherInterface) -> Optional[MessageChain]:
        ariadne = Ariadne.current()
        name: Optional[str] = self.name if isinstance(self.name, str) else None
        if self.name is True:
            if isinstance(interface.event, GroupMessage):
                name = (await ariadne.get_member(interface.event.sender.group, ariadne.account)).name
            else:
                name = (await ariadne.get_bot_profile()).nickname
        first: Element = chain[0]
        if isinstance(name, str) and isinstance(first, Plain) and str(first).startswith(name):
            return chain.removeprefix(name).removeprefix(" ")
        if isinstance(first, At) and first.target == ariadne.account:
            return MessageChain(chain.__root__[1:], inline=True).removeprefix(" ")
        raise ExecutionStop


class Mention(ChainDecorator):
    """At 或提到指定账号/名称"""

    def __init__(self, target: Union[int, str]) -> None:
        """
        Args:
            target (Union[int, str]): 要提到的账号或者名称, \
            如果是 int 则是账号, 如果是 str 则是名称
        """
        self.person: Union[int, str] = target

    async def __call__(self, chain: MessageChain, _) -> Optional[MessageChain]:
        first: Element = chain[0]
        if (
            chain
            and isinstance(first, Plain)
            and isinstance(self.person, str)
            and str(first).startswith(self.person)
        ):
            return chain.removeprefix(self.person).removeprefix(" ")
        if isinstance(first, At) and isinstance(self.person, int) and first.target == self.person:
            return MessageChain(chain.__root__[1:], inline=True).removeprefix(" ")

        raise ExecutionStop


class ContainKeyword(ChainDecorator):
    """消息中含有指定关键字"""

    def __init__(self, keyword: str) -> None:
        """初始化

        Args:
            keyword (str): 关键字
        """
        self.keyword: str = keyword

    async def __call__(self, chain: MessageChain, _) -> Optional[MessageChain]:
        if self.keyword not in chain:
            raise ExecutionStop
        return chain


class MatchContent(ChainDecorator):
    """匹配字符串 / 消息链"""

    def __init__(self, content: Union[str, MessageChain]) -> None:
        """初始化

        Args:
            content (Union[str, MessageChain]): 匹配内容
        """
        self.content: Union[str, MessageChain] = content

    async def __call__(self, chain: MessageChain, _) -> Optional[MessageChain]:
        if isinstance(self.content, str) and str(chain) != self.content:
            raise ExecutionStop
        if isinstance(self.content, MessageChain) and chain != self.content:
            raise ExecutionStop
        return chain


class MatchRegex(ChainDecorator, BaseDispatcher):
    """匹配正则表达式"""

    def __init__(self, regex: str, flags: re.RegexFlag = re.RegexFlag(0), full: bool = True) -> None:
        """初始化匹配正则表达式.

        Args:
            regex (str): 正则表达式
            flags (re.RegexFlag): 正则表达式标志
            full (bool): 是否要求完全匹配, 默认为 True.
        """
        self.regex: str = regex
        self.flags: re.RegexFlag = flags
        self.pattern = re.compile(self.regex, self.flags)
        self.match_func = self.pattern.fullmatch if full else self.pattern.match

    async def __call__(self, chain: MessageChain, _) -> Optional[MessageChain]:
        if not self.match_func(str(chain)):
            raise ExecutionStop
        return chain

    async def beforeExecution(self, interface: DispatcherInterface[MessageEvent]):
        _mapping_str, _map = interface.event.message_chain._to_mapping_str()
        if res := self.match_func(_mapping_str):
            interface.local_storage["__parser_regex_match_obj__"] = res
            interface.local_storage["__parser_regex_match_map__"] = _map
        else:
            raise ExecutionStop

    async def catch(self, interface: DispatcherInterface[MessageEvent]):
        if interface.annotation is re.Match:
            return interface.local_storage["__parser_regex_match_obj__"]


class RegexGroup(Decorator):
    """正则表达式组的标志
    以 `Annotated[MessageChain, RegexGroup("xxx")]` 的形式使用,
    或者作为 Decorator 使用.
    """

    def __init__(self, target: Union[int, str]) -> None:
        """初始化

        Args:
            target (Union[int, str]): 目标的组名或序号
        """
        self.assign_target = target

    async def __call__(self, _, interface: DispatcherInterface[MessageEvent]):
        _res: re.Match = interface.local_storage["__parser_regex_match_obj__"]
        match_group: Tuple[str] = _res.groups()
        match_group_dict: Dict[str, str] = _res.groupdict()
        origin: Optional[str] = None
        if isinstance(self.assign_target, str) and self.assign_target in match_group_dict:
            origin = match_group_dict[self.assign_target]
        elif isinstance(self.assign_target, int) and self.assign_target < len(match_group):
            origin = match_group[self.assign_target]

        return (
            MessageChain._from_mapping_string(origin, interface.local_storage["__parser_regex_match_map__"])
            if origin is not None
            else None
        )

    async def target(self, interface: DecoratorInterface):
        return self("", interface.dispatcher_interface)


class MatchTemplate(ChainDecorator):
    """模板匹配"""

    def __init__(self, template: List[Union[Type[Element], Element, str]]) -> None:
        """初始化

        Args:
            template (List[Union[Type[Element], Element]]): \
                匹配模板，可以为 `Element` 类或其 `Union`, `str`, `Plain` 实例
        """
        self.template: List[Union[Tuple[Type[Element], ...], Element, str]] = []
        for element in template:
            if element is Plain:
                element = "*"
            if isinstance(element, type):
                self.template.append((element,))
            elif get_origin(element) in Unions:  # Union
                assert Plain not in get_args(element), "Leaving Plain here leads to ambiguity"  # TODO
                self.template.append(get_args(element))
            elif isinstance(element, Element) and not isinstance(element, Plain):
                self.template.append(element)
            else:
                element = (
                    re.escape(element.text)
                    if isinstance(element, Plain)
                    else fnmatch.translate(element)[:-2]  # truncating the ending \Z
                )
                if self.template and isinstance(self.template[-1], str):
                    self.template[-1] += element
                else:
                    self.template.append(element)

    def match(self, chain: MessageChain):
        """匹配消息链"""
        chain = chain.as_sendable()
        if len(self.template) != len(chain):
            return False
        for element, template in zip(chain, self.template):
            if isinstance(template, tuple) and not isinstance(element, template):
                return False
            elif isinstance(template, Element) and element != template:
                return False
            elif isinstance(template, str):
                if not isinstance(element, Plain) or not re.match(template, element.text):
                    return False
        return True

    async def __call__(self, chain: MessageChain, _) -> Optional[MessageChain]:
        if not self.match(chain):
            raise ExecutionStop
        return chain


class FuzzyMatch(ChainDecorator):
    """模糊匹配

    Warning:
        我们更推荐使用 FuzzyDispatcher 来进行模糊匹配操作, 因为其具有上下文匹配数量限制.
    """

    def __init__(self, template: str, min_rate: float = 0.6) -> None:
        """初始化

        Args:
            template (str): 模板字符串
            min_rate (float): 最小匹配阈值
        """
        self.template: str = template
        self.min_rate: float = min_rate

    def match(self, chain: MessageChain):
        """匹配消息链"""
        text_frags: List[str] = []
        for element in chain:
            if isinstance(element, Plain):
                text_frags.append(element.text)
            else:
                text_frags.append(str(element))
        text = "".join(text_frags)
        matcher = difflib.SequenceMatcher(a=text, b=self.template)
        # return false when **any** ratio calc falls undef the rate
        if matcher.real_quick_ratio() < self.min_rate:
            return False
        if matcher.quick_ratio() < self.min_rate:
            return False
        return matcher.ratio() >= self.min_rate

    async def __call__(self, chain: MessageChain, _) -> Optional[MessageChain]:
        if not self.match(chain):
            raise ExecutionStop
        return chain


class FuzzyDispatcher(BaseDispatcher):
    scope_map: ClassVar[DefaultDict[str, List[str]]] = defaultdict(list)
    event_ref: ClassVar["Dict[int, Dict[str, Tuple[str, float]]]"] = {}

    def __init__(self, template: str, min_rate: float = 0.6, scope: str = "") -> None:
        """初始化

        Args:
            template (str): 模板字符串
            min_rate (float): 最小匹配阈值
            scope (str): 作用域
        """
        self.template: str = template
        self.min_rate: float = min_rate
        self.scope: str = scope
        self.scope_map[scope].append(template)

    async def beforeExecution(self, interface: DispatcherInterface):
        event = interface.event
        if id(event) not in self.event_ref:
            chain: MessageChain = await interface.lookup_param("message_chain", MessageChain, None)
            text_frags: List[str] = []
            for element in chain:
                if isinstance(element, Plain):
                    text_frags.append(element.text)
                else:
                    text_frags.append(str(element))
            text = "".join(text_frags)
            matcher = difflib.SequenceMatcher()
            matcher.set_seq2(text)
            rate_calc = self.event_ref[id(event)] = {}
            weakref.finalize(event, lambda d: self.event_ref.pop(d), id(event))
            for scope, templates in self.scope_map.items():
                max_match: float = 0.0
                for template in templates:
                    matcher.set_seq1(template)
                    if matcher.real_quick_ratio() < max_match:
                        continue
                    if matcher.quick_ratio() < max_match:
                        continue
                    if matcher.ratio() < max_match:
                        continue
                    rate_calc[scope] = (template, matcher.ratio())
                    max_match = matcher.ratio()
        win_template, win_rate = self.event_ref[id(event)].get(self.scope, (self.template, 0.0))
        if win_template != self.template or win_rate < self.min_rate:
            raise ExecutionStop

    async def catch(self, i: DispatcherInterface) -> Optional[float]:
        event = i.event
        _, rate = self.event_ref[id(event)].get(self.scope, (self.template, 0.0))
        if generic_issubclass(float, i.annotation) and "rate" in i.name:
            return rate


StartsWith = DetectPrefix
EndsWith = DetectSuffix
