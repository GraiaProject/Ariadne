from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.decorator import DecoratorInterface

from ...event.message import MessageEvent
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

    def target(self, interface: DecoratorInterface):
        if not isinstance(interface.event, MessageEvent):
            raise ExecutionStop
        header = interface.event.messageChain.include(Quote, Source)
        rest: MessageChain = interface.event.messageChain.exclude(Quote, Source)
        if not rest.startswith(self.prefix):
            raise ExecutionStop
        result = rest.removeprefix(self.prefix)
        if interface.annotation is MessageChain:
            return header + result


class DetectSuffix(Decorator):
    """后缀检测器"""

    pre = True

    def __init__(self, suffix: str) -> None:
        """初始化后缀检测器.

        Args:
            suffix (str): 要匹配的后缀
        """
        self.suffix = suffix

    def target(self, interface: DecoratorInterface):
        if not isinstance(interface.event, MessageEvent):
            raise ExecutionStop
        header = interface.event.messageChain.include(Quote, Source)
        rest: MessageChain = interface.event.messageChain.exclude(Quote, Source)
        if not rest.endswith(self.suffix):
            raise ExecutionStop
        result = rest.removesuffix(self.suffix)
        if interface.annotation is MessageChain:
            return header + result
