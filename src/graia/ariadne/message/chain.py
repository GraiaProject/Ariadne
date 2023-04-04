"""Ariadne 消息链的实现"""
import re
from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)
from typing_extensions import Self

from graia.amnesia.json import Json
from graia.amnesia.message import MessageChain as BaseMessageChain

from ..model import AriadneBaseModel
from ..util import gen_subclass, unescape_bracket
from .element import (
    At,
    AtAll,
    Element,
    Face,
    File,
    Image,
    MultimediaElement,
    Plain,
    Quote,
    Source,
    _update_forward_refs,
)

if TYPE_CHECKING:
    from ..typing import ReprArgs


Element_T = TypeVar("Element_T", bound=Element)

ELEMENT_MAPPING: Dict[str, Type[Element]] = {
    i.__fields__["type"].default: i for i in gen_subclass(Element) if hasattr(i.__fields__["type"], "default")
}
ORDINARY_ELEMENT_TYPES = frozenset([Plain, Image, Face, At, AtAll, Source, Quote])

MessageOrigin = Union[str, Element]

MessageContainer = Union[MessageOrigin, Sequence["MessageContainer"], "MessageChain"]


class MessageChain(BaseMessageChain, AriadneBaseModel):
    """
    即 "消息链", 被用于承载整个消息内容的数据结构, 包含有一有序列表, 包含有元素实例.
    """

    __root__: List[Element]
    """底层元素列表"""

    @property
    def content(self) -> List[Element]:
        """Amnesia MessageChain 的内容代理"""
        return self.__root__

    @staticmethod
    def build_chain(obj: Union[List[Dict], MessageContainer]) -> List[Element]:
        """内部接口, 会自动反序列化对象并生成.

        Args:
            obj (_Parsable): 需要反序列化的对象

        Returns:
            List[Element]: 内部承载有尽量有效的消息元素的列表
        """
        # single object
        if isinstance(obj, MessageChain):
            return deepcopy(obj.content)
        if isinstance(obj, Element):
            return [obj]
        if isinstance(obj, str):
            return [Plain(obj)]
        element_list: List[Element] = []
        for o in obj:
            if isinstance(o, dict):
                if typ := ELEMENT_MAPPING.get(o.get("type", "Unknown")):
                    element_list.append(typ.parse_obj(o))
            else:
                element_list.extend(MessageChain.build_chain(o))

        special_cnt: int = sum(element.__class__ not in ORDINARY_ELEMENT_TYPES for element in element_list)

        if special_cnt > 1:
            raise ValueError("An MessageChain can only contain *one* special element")
        return element_list

    @classmethod
    def parse_obj(cls: Type[Self], obj: Union[List[dict], List[Element]]) -> Self:
        """解析 MessageChain.

        Args:
            obj (List[T]): 需要反序列化的对象

        Returns:
            MessageChain: 内部承载有尽量有效的消息元素的消息链
        """
        return cls(cls.build_chain(obj), inline=True)

    @overload
    def __init__(self, __root__: Sequence[Element], *, inline: Literal[True]) -> None:
        ...

    @overload
    def __init__(self, *elements: MessageContainer, inline: Literal[False] = False) -> None:
        ...

    def __init__(
        self,
        __root__: MessageContainer,
        *elements: MessageContainer,
        inline: bool = False,
    ) -> None:
        """
        创建消息链.

        Args:
            *elements (Union[Iterable[Element], Element, str]): \
            元素的容器, 为承载元素的可迭代对象/单元素实例, \
            字符串会被自动不可逆的转换为 `Plain`

        Returns:
            MessageChain: 创建的消息链
        """
        if not inline:
            AriadneBaseModel.__init__(
                self,
                __root__=self.build_chain((__root__, *elements)),
            )
        else:
            AriadneBaseModel.__init__(self, __root__=[])
            self.__root__ = __root__  # type: ignore

    def __repr_args__(self) -> "ReprArgs":
        return [(None, list(self.content))]

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
        return super().__getitem__(item)

    def as_sendable(self) -> Self:
        """将消息链转换为可发送形式 (去除 File)

        Returns:
            MessageChain: 转换后的消息链.
        """
        return self.exclude(File)

    def get(self, element_class: Type[Element_T], count: int = -1) -> List[Element_T]:
        res = super().get(element_class, count)
        if isinstance(res, (Quote, Source)):
            raise IndexError(
                (
                    "MessageChain.get(Quote/Source) is removed in 0.10.0.\n"
                    "See https://github.com/GraiaProject/Ariadne/blob/dev/CHANGELOG.md#095"
                ),
            )
        return res

    def __eq__(self, other: Union[MessageContainer, Self]) -> bool:
        if id(self) == id(other):
            return True
        if not isinstance(other, (MessageChain, list)):
            return False
        if not isinstance(other, MessageChain):
            other = MessageChain(other)
        return other.content == self.content

    def __mul__(self, time: int) -> Self:
        result = []
        for _ in range(time):
            result.extend(deepcopy(self.content))
        return MessageChain(result, inline=True)

    def __imul__(self, time: int) -> Self:
        result = []
        for _ in range(time):
            result.extend(deepcopy(self.content))
        self.content.clear()
        self.content.extend(result)
        return self

    def __len__(self) -> int:
        return len(self.content)

    def as_persistent_string(
        self,
        *,
        binary: bool = True,
        include: Iterable[Type[Element]] = (),
        exclude: Iterable[Type[Element]] = (),
    ) -> str:
        """转换为持久化字符串.

        Args:
            binary (bool, optional): 是否附带图片或声音的二进制. 默认为 True.
            include (Iterable[Type[Element]], optional): 筛选, 只包含本参数提供的元素类型.
            exclude (Iterable[Type[Element]], optional): 筛选, 排除本参数提供的元素类型.

        Raises:
            ValueError: 同时提供 include 与 exclude

        Returns:
            str: 持久化字符串. 不是 Mirai Code.
        """
        string_list = []
        include = tuple(include)
        exclude = tuple(exclude)
        if include and exclude:
            raise ValueError("Can not present include and exclude at same time!")
        for i in self.content:
            if (
                (include and isinstance(i, include))
                or (exclude and not isinstance(i, exclude))
                or not (include or exclude)
            ):
                if isinstance(i, Plain):
                    string_list.append(i.as_persistent_string().replace("[", "[_"))
                elif not isinstance(i, MultimediaElement):
                    string_list.append(i.as_persistent_string())
                else:
                    string_list.append(i.as_persistent_string(binary=binary))
        return "".join(string_list)

    async def download_binary(self) -> Self:
        """下载消息中所有的二进制数据并保存在元素实例内"""
        for elem in self.content:
            if isinstance(elem, MultimediaElement):
                await elem.get_bytes()
        return self

    @classmethod
    def from_persistent_string(cls, string: str) -> Self:
        """从持久化字符串生成消息链.

        Returns:
            MessageChain: 还原的消息链.
        """
        result: List[Element] = []
        for match in re.split(r"(\[mirai:.+?\])", string):
            if mirai := re.fullmatch(r"\[mirai:(.+?)(:(.+?))\]", match):
                j_string = mirai[3]
                element_cls = ELEMENT_MAPPING[mirai[1]]
                result.append(element_cls.parse_obj(Json.deserialize(unescape_bracket(j_string))))
            elif match:
                result.append(Plain(match.replace("[_", "[")))
        return MessageChain(result, inline=True)

    def _to_mapping_str(
        self,
        *,
        remove_source: bool = True,
        remove_quote: bool = True,
        remove_extra_space: bool = False,
    ) -> Tuple[str, Dict[str, Element]]:
        """转换消息链为映射字符串与映射字典的元组.

        Args:
            remove_source (bool, optional): 是否移除消息链中的 Source 元素. 默认为 True.
            remove_quote (bool, optional): 是否移除消息链中的 Quote 元素. 默认为 True.
            remove_extra_space (bool, optional): 是否移除 Quote At AtAll 的多余空格. 默认为 False.

        Returns:
            Tuple[str, Dict[str, Element]]: 生成的映射字符串与映射字典的元组
        """
        elem_mapping: Dict[str, Element] = {}
        elem_str_list: List[str] = []
        for i, elem in enumerate(self.content):
            if not isinstance(elem, Plain):
                if remove_quote and isinstance(elem, Quote):
                    continue
                if remove_source and isinstance(elem, Source):
                    continue
                elem_mapping[str(i)] = elem
                elem_str_list.append(f"\x02{i}_{elem.type}\x03")
            elif (
                remove_extra_space
                and i  # not first element
                and isinstance(
                    self.content[i - 1], (Quote, At, AtAll)
                )  # following elements which have an dumb trailing space
                and elem.text.startswith("  ")  # extra space (count >= 2)
            ):
                elem_str_list.append(elem.text[1:])
            else:
                elem_str_list.append(elem.text)
        return "".join(elem_str_list), elem_mapping

    __element_pattern = re.compile("(\x02\\w+\x03)")

    @classmethod
    def _from_mapping_string(cls, string: str, mapping: Dict[str, Element]) -> Self:
        """从映射字符串与映射字典的元组还原消息链.

        Args:
            string (str): 映射字符串
            mapping (Dict[int, Element]): 映射字典.

        Returns:
            MessageChain: 构建的消息链
        """
        elements: List[Element] = []
        for x in cls.__element_pattern.split(string):
            if x:
                if x[0] == "\x02" and x[-1] == "\x03":
                    index, class_name = x[1:-1].split("_")
                    if not isinstance(mapping[index], ELEMENT_MAPPING[class_name]):
                        raise ValueError("Validation failed: not matching element type!")
                    elements.append(mapping[index])
                else:
                    elements.append(Plain(x))
        return cls(elements, inline=True)

    def removeprefix(self, prefix: str, *, copy: bool = True, skip_header: bool = True) -> Self:
        """移除消息链前缀.

        Args:
            prefix (str): 要移除的前缀.
            copy (bool, optional): 是否在副本上修改, 默认为 True.
            skip_header (bool, optional): 是否要忽略 Source 与 Quote 类型查找, \
                默认为 True. (移除后仍会带上 Source 与 Quote)

        Returns:
            MessageChain: 修改后的消息链, 若未移除则原样返回.
        """
        header = []
        elements = []
        if not skip_header:
            elements = self.content[:]
        else:
            for element in self.content:
                if isinstance(element, (Quote, Source)):
                    header.append(element)
                else:
                    elements.append(element)
        if copy:
            header = deepcopy(header)
            elements = deepcopy(elements)
        if not elements or not isinstance(elements[0], Plain):
            return self.copy() if copy else self
        if elements[0].text.startswith(prefix):
            elements[0].text = elements[0].text[len(prefix) :]
        if copy:
            return MessageChain(header + elements, inline=True)
        self.content.clear()
        self.content.extend(header + elements)
        return self

    def removesuffix(self, suffix: str, *, copy: bool = True) -> Self:
        """移除消息链后缀.

        Args:
            suffix (str): 要移除的后缀.
            copy (bool, optional): 是否在副本上修改, 默认为 True.

        Returns:
            MessageChain: 修改后的消息链, 若未移除则原样返回.
        """
        elements = deepcopy(self.content) if copy else self.content
        if not elements or not isinstance(elements[-1], Plain):
            return self.copy() if copy else self
        last_elem: Plain = elements[-1]
        if last_elem.text.endswith(suffix):
            last_elem.text = last_elem.text[: -len(suffix)]
        if copy:
            return MessageChain(elements, inline=True)
        self.content.clear()
        self.content.extend(elements)
        return self

    def replace(
        self,
        old: MessageContainer,
        new: MessageContainer,
    ) -> Self:
        """替换消息链中的一部分. (在副本上操作)

        Args:
            old (MessageChain): 要替换的消息链.
            new (MessageChain): 替换后的消息链.

        Returns:
            MessageChain: 修改后的消息链, 若未替换则原样返回.
        """
        if not isinstance(old, MessageChain):
            old = MessageChain(old)
        if not isinstance(new, MessageChain):
            new = MessageChain(new)
        index_list: List[int] = self.index_sub(old)

        def unzip(chain: Self) -> List[Union[str, Element]]:
            unzipped: List[Union[str, Element]] = []
            for e in chain.content:
                if isinstance(e, Plain):
                    unzipped.extend(e.text)
                else:
                    unzipped.append(e)
            return unzipped

        unzipped_new: List[Union[str, Element]] = unzip(new)
        unzipped_old: List[Union[str, Element]] = unzip(old)
        unzipped_self: List[Union[str, Element]] = unzip(self)
        unzipped_result: List[Union[str, Element]] = []
        last_end: int = 0
        for start in index_list:
            unzipped_result.extend(unzipped_self[last_end:start])
            last_end = start + len(unzipped_old)
            unzipped_result.extend(unzipped_new)
        unzipped_result.extend(unzipped_self[last_end:])
        # Merge result
        result_list: List[Element] = []
        char_stk: List[str] = []
        for v in unzipped_result:
            if isinstance(v, str):
                char_stk.append(v)
            else:
                result_list.append(Plain("".join(char_stk)))
                char_stk = []
                result_list.append(v)
        if char_stk:
            result_list.append(Plain("".join(char_stk)))
        return MessageChain(result_list, inline=True)

    @property
    def display(self) -> str:
        """获取消息链的显示字符串.

        Returns:
            str: 消息链的显示字符串.
        """
        return str(self)

    @property
    def safe_display(self) -> str:
        """获取消息链的安全显示字符串. (对特殊字符进行转义了)

        Returns:
            str: 消息链的安全显示字符串.
        """
        return repr(str(self))[1:-1]

    def __hash__(self) -> int:
        return id(self)


_update_forward_refs()
