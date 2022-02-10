"""Ariadne 基础的 parser, 包括 DetectPrefix 与 DetectSuffix"""
import re
from typing import Union

from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.decorator import DecoratorInterface

from ...app import Ariadne
from ...event.message import GroupMessage
from ..chain import MessageChain
from ..element import At, Element, Plain, Quote, Source


class DetectPrefix(Decorator):
    """前缀检测器"""

    pre = True

    def __init__(self, prefix: str) -> None:
        """初始化前缀检测器.

        Args:
            prefix (str): 要匹配的前缀
        """
        self.prefix = prefix

    async def target(self, interface: DecoratorInterface):
        """检测前缀并 decorate 参数"""
        chain: MessageChain = await interface.dispatcher_interface.lookup_param(
            "message_chain", MessageChain, None
        )
        header = chain.include(Quote, Source)
        rest: MessageChain = chain.exclude(Quote, Source)
        if not rest.startswith(self.prefix):
            raise ExecutionStop
        result = rest.removeprefix(self.prefix)
        if interface.annotation is MessageChain:
            return header + result
        return None


class DetectSuffix(Decorator):
    """后缀检测器"""

    pre = True

    def __init__(self, suffix: str) -> None:
        """初始化后缀检测器.

        Args:
            suffix (str): 要匹配的后缀
        """
        self.suffix = suffix

    async def target(self, interface: DecoratorInterface):
        """检测后缀并 decorate 参数"""
        chain: MessageChain = await interface.dispatcher_interface.lookup_param(
            "message_chain", MessageChain, None
        )
        header = chain.include(Quote, Source)
        rest: MessageChain = chain.exclude(Quote, Source)
        if not rest.endswith(self.suffix):
            raise ExecutionStop
        result = rest.removesuffix(self.suffix)
        if interface.annotation is MessageChain:
            return header + result
        return None


class MentionMe(Decorator):
    """At 账号或者提到账号群昵称"""

    pre = True

    @staticmethod
    async def target(interface: DecoratorInterface):

        ariadne = Ariadne.get_running(Ariadne)
        chain: MessageChain = await interface.dispatcher_interface.lookup_param(
            "message_chain", MessageChain, None
        )
        if isinstance(interface.event, GroupMessage):
            name = (await ariadne.getMemberInfo(ariadne.account, interface.event.sender.group)).name
        else:
            name = (await ariadne.getBotProfile()).nickname
        header = chain.include(Quote, Source)
        rest: MessageChain = chain.exclude(Quote, Source)
        first: Element = rest[0]
        if rest and isinstance(first, Plain):
            if first.asDisplay().startswith(name):
                return header + rest.removeprefix(name).removeprefix(" ")
        if rest and isinstance(first, At):
            if first.target == ariadne.account:
                return header + rest[1:].removeprefix(" ")

        raise ExecutionStop


class Mention(Decorator):
    """At 或提到指定人"""

    pre = True

    def __init__(self, target: Union[int, str]) -> None:
        self.target: Union[int, str] = target

    async def target(self, interface: DecoratorInterface):
        chain: MessageChain = await interface.dispatcher_interface.lookup_param(
            "message_chain", MessageChain, None
        )
        header = chain.include(Quote, Source)
        rest: MessageChain = chain.exclude(Quote, Source)
        first: Element = rest[0]
        if rest and isinstance(first, Plain):
            if isinstance(self.target, str) and first.asDisplay().startswith(self.target):
                return header + rest.removeprefix(self.target).removeprefix(" ")
        if rest and isinstance(first, At):
            if isinstance(self.target, int) and first.target == self.target:
                return header + rest[1:].removeprefix(" ")

        raise ExecutionStop


class ContainKeyword(Decorator):
    """消息中含有指定关键字"""

    pre = True

    def __init__(self, keyword: str) -> None:
        self.keyword: str = keyword

    async def target(self, interface: DecoratorInterface):
        chain: MessageChain = await interface.dispatcher_interface.lookup_param(
            "message_chain", MessageChain, None
        )
        if self.keyword not in chain:
            raise ExecutionStop


class MatchContent(Decorator):
    """匹配字符串 / 消息链"""

    pre = True

    def __init__(self, content: Union[str, MessageChain]) -> None:
        self.content: Union[str, MessageChain] = content

    async def target(self, interface: DecoratorInterface):
        chain: MessageChain = await interface.dispatcher_interface.lookup_param(
            "message_chain", MessageChain, None
        )
        if isinstance(self.content, str) and chain.asDisplay() != self.content:
            raise ExecutionStop
        if isinstance(self.content, MessageChain) and chain != self.content:
            raise ExecutionStop


class MatchRegex(Decorator):
    """匹配正则表达式"""

    pre = True

    def __init__(self, regex: str, flags: re.RegexFlag = re.RegexFlag(0)) -> None:
        """初始化匹配正则表达式.

        Args:
            regex (str): 正则表达式
            flags (re.RegexFlag): 正则表达式标志
        """
        self.regex: str = regex
        self.flags: re.RegexFlag = flags

    async def target(self, interface: DecoratorInterface):
        chain: MessageChain = await interface.dispatcher_interface.lookup_param(
            "message_chain", MessageChain, None
        )
        if not re.match(self.regex, chain.asDisplay(), self.flags):
            raise ExecutionStop
