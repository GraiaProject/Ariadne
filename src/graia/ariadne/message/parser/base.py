"""Ariadne 基础的 parser, 包括 DetectPrefix 与 DetectSuffix"""
import abc
import difflib
import fnmatch
import re
import weakref
from typing import ClassVar, DefaultDict, Dict, List, Optional, Tuple, Type, Union

from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.decorator import DecoratorInterface
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from loguru import logger

from ... import get_running
from ...event.message import GroupMessage
from ...typing import generic_issubclass
from ..chain import MessageChain
from ..element import At, Element, Plain, Quote, Source


class Compose(Decorator):
    """将多个基础 Decorator 串联起来"""

    def __init__(self, *deco: "ChainDecorator") -> None:
        self.deco: List[ChainDecorator] = list(deco)

    async def target(self, interface: DecoratorInterface):
        chain = await interface.dispatcher_interface.lookup_param("message_chain", MessageChain, None)
        for deco in self.deco:
            chain = await deco.decorate(chain, interface)
            if chain is None:
                break
        if interface.annotation is MessageChain:
            if chain is None:
                raise ExecutionStop
            return chain


class ChainDecorator(abc.ABC, Decorator):
    pre = True

    @abc.abstractmethod
    async def decorate(self, chain: MessageChain, interface: DecoratorInterface) -> Optional[MessageChain]:
        ...

    async def target(self, interface: DecoratorInterface):
        return await self.decorate(
            await interface.dispatcher_interface.lookup_param("message_chain", MessageChain, None), interface
        )


class DetectPrefix(ChainDecorator):
    """前缀检测器"""

    def __init__(self, prefix: str) -> None:
        """初始化前缀检测器.

        Args:
            prefix (str): 要匹配的前缀
        """
        self.prefix = prefix

    async def decorate(self, chain: MessageChain, interface: DecoratorInterface) -> Optional[MessageChain]:
        header = chain.include(Quote, Source)
        rest: MessageChain = chain.exclude(Quote, Source)
        if not rest.startswith(self.prefix):
            raise ExecutionStop
        result = rest.removeprefix(self.prefix).removeprefix(" ")
        if interface.annotation is MessageChain:
            return header + result


class DetectSuffix(ChainDecorator):
    """后缀检测器"""

    def __init__(self, suffix: str) -> None:
        """初始化后缀检测器.

        Args:
            suffix (str): 要匹配的后缀
        """
        self.suffix = suffix

    async def decorate(self, chain: MessageChain, interface: DecoratorInterface) -> Optional[MessageChain]:
        header = chain.include(Quote, Source)
        rest: MessageChain = chain.exclude(Quote, Source)
        if not rest.endswith(self.suffix):
            raise ExecutionStop
        result = rest.removesuffix(self.suffix).removesuffix(" ")
        if interface.annotation is MessageChain:
            return header + result


class MentionMe(ChainDecorator):
    """At 账号或者提到账号群昵称"""

    async def decorate(self, chain: MessageChain, interface: DecoratorInterface) -> Optional[MessageChain]:
        ariadne = get_running()
        if isinstance(interface.event, GroupMessage):
            if not ariadne.account:
                logger.warning("Unable to detect Ariadne's name because account is not set")
                raise ExecutionStop
            name = (await ariadne.getMember(interface.event.sender.group, ariadne.account)).name
        else:
            name = (await ariadne.getBotProfile()).nickname
        header = chain.include(Quote, Source)
        rest: MessageChain = chain.exclude(Quote, Source)
        first: Element = rest[0]
        result: Optional[MessageChain] = None
        if rest and isinstance(first, Plain) and first.asDisplay().startswith(name):
            result = header + rest.removeprefix(name).removeprefix(" ")
        if rest and isinstance(first, At) and first.target == ariadne.account:
            result = header + MessageChain(rest.__root__[1:], inline=True).removeprefix(" ")

        if result is None:
            raise ExecutionStop
        if interface.annotation is MessageChain:
            return result


class Mention(ChainDecorator):
    """At 或提到指定人"""

    def __init__(self, target: Union[int, str]) -> None:
        self.person: Union[int, str] = target

    async def decorate(self, chain: MessageChain, interface: DecoratorInterface) -> Optional[MessageChain]:
        header = chain.include(Quote, Source)
        rest: MessageChain = chain.exclude(Quote, Source)
        first: Element = rest[0]
        result: Optional[MessageChain] = None
        if (
            rest
            and isinstance(first, Plain)
            and isinstance(self.person, str)
            and first.asDisplay().startswith(self.person)
        ):
            result = header + rest.removeprefix(self.person).removeprefix(" ")
        if rest and isinstance(first, At) and isinstance(self.person, int) and first.target == self.person:
            result = header + MessageChain(rest.__root__[1:], inline=True).removeprefix(" ")

        if result is None:
            raise ExecutionStop
        if interface.annotation is MessageChain:
            return result


class ContainKeyword(ChainDecorator):
    """消息中含有指定关键字"""

    def __init__(self, keyword: str) -> None:
        self.keyword: str = keyword

    async def decorate(self, chain: MessageChain, interface: DecoratorInterface) -> Optional[MessageChain]:
        if self.keyword not in chain:
            raise ExecutionStop
        if interface.annotation is MessageChain:
            return chain


class MatchContent(ChainDecorator):
    """匹配字符串 / 消息链"""

    def __init__(self, content: Union[str, MessageChain]) -> None:
        self.content: Union[str, MessageChain] = content
        self.next: Optional[ChainDecorator] = None

    async def decorate(self, chain: MessageChain, interface: DecoratorInterface) -> Optional[MessageChain]:
        if isinstance(self.content, str) and chain.asDisplay() != self.content:
            raise ExecutionStop
        if isinstance(self.content, MessageChain) and chain != self.content:
            raise ExecutionStop
        if interface.annotation is MessageChain:
            return chain


class MatchRegex(ChainDecorator):
    """匹配正则表达式"""

    def __init__(self, regex: str, flags: re.RegexFlag = re.RegexFlag(0)) -> None:
        """初始化匹配正则表达式.

        Args:
            regex (str): 正则表达式
            flags (re.RegexFlag): 正则表达式标志
        """
        self.regex: str = regex
        self.flags: re.RegexFlag = flags

    async def decorate(self, chain: MessageChain, interface: DecoratorInterface) -> Optional[MessageChain]:
        if not re.match(self.regex, chain.asDisplay(), self.flags):
            raise ExecutionStop
        if interface.annotation is MessageChain:
            return chain


class MatchTemplate(ChainDecorator):
    """模板匹配"""

    def __init__(self, template: List[Union[Type[Element], Element]]) -> None:
        self.template: List[Union[Type[Element], Element, str]] = []
        for element in template:
            if isinstance(element, type) and element is not Plain:
                self.template.append(element)
            elif isinstance(element, Element) and not isinstance(element, Plain):
                self.template.append(element)
            else:
                element = element.text if isinstance(element, Plain) else "*"
                if self.template and isinstance(self.template[-1], str):
                    self.template[-1] = self.template[-1] + element
                else:
                    self.template.append(element)

    def match(self, chain: MessageChain):
        """匹配消息链"""
        chain = chain.asSendable()
        if len(self.template) != len(chain):
            return False
        for element, template in zip(chain, self.template):
            if isinstance(template, type) and not isinstance(element, template):
                return False
            elif isinstance(template, Element) and element != template:
                return False
            elif isinstance(template, str):
                if not isinstance(element, Plain) or not fnmatch.fnmatch(element.text, template):
                    return False
        return True

    async def decorate(self, chain: MessageChain, interface: DecoratorInterface) -> Optional[MessageChain]:
        if not self.match(chain):
            raise ExecutionStop
        if interface.annotation is MessageChain:
            return chain


class FuzzyMatch(ChainDecorator):
    """模糊匹配

    Warning:
        我们更推荐使用 FuzzyDispatcher 来进行模糊匹配操作, 因为其具有上下文匹配数量限制.
    """

    def __init__(self, template: str, min_rate: float = 0.6) -> None:
        self.template: str = template
        self.min_rate: float = min_rate

    def match(self, chain: MessageChain):
        """匹配消息链"""
        text_frags: List[str] = []
        for element in chain:
            if isinstance(element, Plain):
                text_frags.append(element.text)
            else:
                text_frags.append(element.asDisplay())
        text = "".join(text_frags)
        matcher = difflib.SequenceMatcher(a=text, b=self.template)
        # return false when **any** ratio calc falls undef the rate
        if matcher.real_quick_ratio() < self.min_rate:
            return False
        if matcher.quick_ratio() < self.min_rate:
            return False
        return matcher.ratio() >= self.min_rate

    async def decorate(self, chain: MessageChain, interface: DecoratorInterface) -> Optional[MessageChain]:
        if not self.match(chain):
            raise ExecutionStop
        if interface.annotation is MessageChain:
            return chain


class FuzzyDispatcher(BaseDispatcher):
    scope_map: ClassVar[DefaultDict[str, List[str]]] = DefaultDict(list)
    event_ref: ClassVar["Dict[int, Dict[str, Tuple[str, float]]]"] = {}

    def __init__(self, template: str, min_rate: float = 0.6, scope: str = "") -> None:
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
                    text_frags.append(element.asDisplay())
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
