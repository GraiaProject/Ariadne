"""Ariadne 基础的 parser, 包括 DetectPrefix 与 DetectSuffix"""
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.decorator import DecoratorInterface

from ..chain import MessageChain
from ..element import Quote, Source


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
            "message_chain", MessageChain, None, []
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
            "message_chain", MessageChain, None, []
        )
        header = chain.include(Quote, Source)
        rest: MessageChain = chain.exclude(Quote, Source)
        if not rest.endswith(self.suffix):
            raise ExecutionStop
        result = rest.removesuffix(self.suffix)
        if interface.annotation is MessageChain:
            return header + result
        return None
