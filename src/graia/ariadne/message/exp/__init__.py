from typing import Literal, Sequence, overload

from ..chain import Element
from ..chain import MessageChain as BaseMessageChain
from ..chain import MessageContainer


class MessageChain(BaseMessageChain):
    """实验性的消息链，`Source` 与 `Quote` 被去除了。"""

    @overload
    def __init__(self, __root__: Sequence[Element], *, inline: Literal[True]) -> None:
        ...

    @overload
    def __init__(self, *elements: MessageContainer, inline: Literal[False] = False) -> None:
        ...

    def __init__(self, *args, **kwargs) -> None:
        """
        创建消息链.

        Args:
            *elements (Union[Iterable[Element], Element, str]): \
            元素的容器, 为承载元素的可迭代对象/单元素实例, \
            字符串会被自动不可逆的转换为 `Plain`

        Returns:
            MessageChain: 创建的消息链
        """
        super().__init__(*args, **kwargs)
