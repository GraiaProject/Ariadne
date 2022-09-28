from typing import Any, List, Literal, Sequence, Tuple, Type, Union, overload

from graia.amnesia.message import MessageChain as ParentMessageChain
from typing_extensions import Self

from ..chain import Element, Element_T
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

    @overload
    def __getitem__(self, item: Tuple[Type[Element_T], int]) -> List[Element_T]:
        ...

    @overload
    def __getitem__(self, item: Type[Element_T]) -> List[Element_T]:
        ...

    @overload
    def __getitem__(self, item: int) -> Element:
        ...

    @overload
    def __getitem__(self, item: slice) -> Self:
        ...

    def __getitem__(self, item: Union[Tuple[Type[Element], int], Type[Element], int, slice]) -> Any:
        """
        可通过切片取出子消息链, 或元素.

        通过 `type, count` 型元组取出前 `count` 个 `type` 元素组成的列表

        通过 `type` 取出属于 `type` 的元素列表

        通过 `int` 取出对应位置元素.

        Args:
            item (Union[Tuple[Type[Element], int], Type[Element], int, slice]): 索引项
        Returns:
            Union[List[Element], Element, MessageChain]: 索引结果.
        """
        if isinstance(item, tuple):
            return self.get(*item)
        if isinstance(item, (int, slice)):
            return ParentMessageChain.__getitem__(self, item)
        return super().__getitem__(item)

    def get(self, element_class: Type[Element_T], count: int = -1) -> List[Element_T]:
        return ParentMessageChain.get(self, element_class, count)
