"""简单的消息链元素选择器"""
from typing import TYPE_CHECKING, Callable, Iterable, List, Optional, Tuple, Type, Union

from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.interfaces.decorator import DecoratorInterface

from .chain import MessageChain
from .element import Element

if TYPE_CHECKING:
    from ..typing import Slice

    ElementFilter = Union[Iterable[Type[Element]], Type[Element], Callable[[Element], bool]]
    Item = Union[Slice[ElementFilter, Optional[int], None], ElementFilter]


class Component(Decorator):
    """简单的消息链元素选择器, 允许使用 __class_getitem__ 实例化"""

    filter: Callable[[Element], bool]
    match_time: int = -1

    def __init__(
        self,
        filter: Union[Tuple[Type[Element], ...], Callable[[Element], bool]],
        match_time: int = -1,
    ) -> None:
        if not callable(filter):

            def matcher(element: Element) -> bool:
                return isinstance(element, filter)

            self.filter = matcher
        else:
            self.filter = filter
        self.match_time = match_time

    def __class_getitem__(cls, item: "Item") -> "Component":
        match_time = -1

        if isinstance(item, slice):
            element_filter = item.start
            match_time = item.stop or match_time
        else:
            element_filter = item

        if isinstance(element_filter, type):
            element_cls = (element_filter,)
        else:
            element_cls = tuple(element_filter)

        return cls(element_cls, match_time)

    def select(self, chain: MessageChain) -> MessageChain:
        """基于实例筛选元素

        Args:
            chain (MessageChain): 输入的消息链

        Returns:
            MessageChain: 筛选后的消息链
        """
        result: List[Element] = []
        matched: int = 0
        for element in chain.__root__:
            if self.filter(element):
                result.append(element)
                matched += 1
            if matched == self.match_time:
                break
        return MessageChain(result, inline=True)

    def target(self, interface: DecoratorInterface) -> MessageChain:
        """用作 Decorator 时使用, 返回处理后的 MessageChain"""
        if not isinstance(interface.return_value, MessageChain):
            raise TypeError(f"Can't cast Component on {type(interface.return_value)}!")
        chain: MessageChain = interface.return_value
        return self.select(chain)
