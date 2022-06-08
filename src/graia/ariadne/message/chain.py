"""Ariadne 消息链的实现"""
import re
from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

from graia.amnesia.json import Json
from graia.amnesia.message import MessageChain as BaseMessageChain
from typing_extensions import Self

from ..model import AriadneBaseModel
from ..util import AttrConvertMixin, deprecated, gen_subclass
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
_Parsable = Union[str, dict, Element, Iterable["_Parsable"], "MessageChain"]


class MessageChain(BaseMessageChain, AriadneBaseModel, AttrConvertMixin):
    """
    即 "消息链", 被用于承载整个消息内容的数据结构, 包含有一有序列表, 包含有元素实例.
    """

    __root__: List[Element]
    """底层元素列表"""

    __text_element_class__ = Plain

    @property
    def content(self) -> List[Element]:
        """Amnesia MessageChain 的内容代理"""
        return self.__root__

    @staticmethod
    def build_chain(obj: _Parsable) -> List[Element]:
        """内部接口, 会自动反序列化对象并生成.

        Args:
            obj (_Parsable): 需要反序列化的对象

        Returns:
            List[Element]: 内部承载有尽量有效的消息元素的列表
        """
        element_list: List[Element] = []

        if isinstance(obj, Element):
            element_list.append(obj)
        elif isinstance(obj, dict):
            if obj.get("type") in ELEMENT_MAPPING:
                element_list.append(ELEMENT_MAPPING[obj["type"]].parse_obj(obj))
        elif isinstance(obj, str):
            element_list.append(Plain(obj))
        elif isinstance(obj, MessageChain):
            element_list.extend(obj.content)
        elif isinstance(obj, Iterable):  # needs to be last
            for o in obj:
                element_list.extend(MessageChain.build_chain(o))

        special_cnt: int = sum(element.__class__ not in ORDINARY_ELEMENT_TYPES for element in element_list)

        if special_cnt > 1:
            raise ValueError("An MessageChain can only contain *one* special element")
        return element_list

    @classmethod
    def parse_obj(cls: Type[Self], obj: List[Union[dict, Element]]) -> Self:
        """内部接口, 会自动将作为外部态的消息元素转为内部态.

        Args:
            obj (List[T]): 需要反序列化的对象

        Returns:
            MessageChain: 内部承载有尽量有效的消息元素的消息链
        """
        return cls(__root__=cls.build_chain(obj))  # type: ignore

    @overload
    def __init__(self, __root__: Iterable[Element], *, inline: Literal[True]) -> None:
        ...

    @overload
    def __init__(self, *elements: _Parsable, inline: Literal[False] = False) -> None:
        ...

    def __init__(
        self,
        __root__: _Parsable,
        *elements: _Parsable,
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
                __root__=MessageChain.build_chain((__root__, *elements)),  # type: ignore
            )
        else:
            AriadneBaseModel.__init__(self, __root__=__root__)  # type: ignore

    def unzip(self) -> List[Union[str, Element]]:
        """解压消息链为元素/单字符列表.

        Return:
            List[Union[str, Element]]: 解压后的元素/字符列表.
        """
        unzipped: List[Union[str, Element]] = []
        for e in self.content:
            if isinstance(e, Plain):
                unzipped.extend(e.text)
            else:
                unzipped.append(e)
        return unzipped

    def has(self, item: Union[Element, Type[Element], Self, str]) -> bool:
        """
        判断消息链中是否含有特定的元素/元素类型/消息链/字符串.

        Args:
            item (Union[Element_T, Type[Element_T], Self]): 需要判断的元素/元素类型/消息链/字符串.

        Returns:
            bool: 判断结果
        """
        if isinstance(item, str):
            return bool(self.find_sub_chain(MessageChain([Plain(item)], inline=True)))
        if isinstance(item, Element):
            return item in self.merge().content
        if isinstance(item, type):
            return item in [type(i) for i in self.content]
        if isinstance(item, MessageChain):
            return bool(self.find_sub_chain(item))
        raise ValueError(f"{item} is not an acceptable argument!")

    def get(self, element_class: Type[Element_T], count: int = -1) -> List[Element_T]:
        """
        获取消息链中所有特定类型的消息元素

        Args:
            element_class (T): 指定的消息元素的类型, 例如 "Plain", "At", "Image" 等.

        Returns:
            List[T]: 获取到的符合要求的所有消息元素; 另: 可能是空列表([]).
        """
        if count == -1:
            count = len(self.content)
        return [i for i in self.content if isinstance(i, element_class)][:count]

    def __str__(self) -> str:
        return "".join(str(e) for e in self.content)

    def __repr_args__(self) -> "ReprArgs":
        return [(None, list(self.content))]

    # define as a method so pydantic won't complain
    def __contains__(self, item: Union[Self, Type[Element_T], Element_T, str]) -> bool:
        """
        是否包含特定对象
        """
        return self.has(item)

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

    def __getitem__(  # type: ignore
        self, item: Union[Tuple[Type[Element_T], int], Type[Element_T], int, slice]
    ) -> Union[List[Element_T], Element, Self]:
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
        if isinstance(item, type) and issubclass(item, Element):
            return self.get(item)
        if isinstance(item, tuple):
            return self.get(*item)
        if isinstance(item, int):
            return self.content[item]
        if isinstance(item, slice):
            return MessageChain(self.content[item], inline=True)
        raise NotImplementedError(f"{item} is not allowed for item getting")

    def find_sub_chain(self, subchain: _Parsable) -> List[int]:
        """判断消息链是否含有子链. 使用 KMP 算法.

        Args:
            subchain (Union[MessageChain, List[Element]]): 要判断的子链.

        Returns:
            List[int]: 所有找到的下标.
        """
        pattern: List[Union[str, Element]] = (
            subchain.unzip() if isinstance(subchain, MessageChain) else MessageChain(subchain).unzip()
        )

        match_target: List[Union[str, Element]] = self.unzip()

        if len(match_target) < len(pattern):
            return []

        fallback: List[int] = [0 for _ in pattern]
        current_fb: int = 0  # current fallback index
        for i in range(1, len(pattern)):
            while current_fb and pattern[i] != pattern[current_fb]:
                current_fb = fallback[current_fb - 1]
            if pattern[i] == pattern[current_fb]:
                current_fb += 1
            fallback[i] = current_fb

        match_index: List[int] = []
        ptr = 0
        for i, e in enumerate(match_target):
            while ptr and e != pattern[ptr]:
                ptr = fallback[ptr - 1]
            if e == pattern[ptr]:
                ptr += 1
            if ptr == len(pattern):
                match_index.append(i - ptr + 1)
                ptr = fallback[ptr - 1]
        return match_index

    def as_sendable(self) -> Self:
        """将消息链转换为可发送形式 (去除 Source, Quote, File)

        Returns:
            MessageChain: 转换后的消息链.
        """
        return self.exclude(Source, Quote, File)

    def __eq__(self, other: Union[_Parsable, Self]) -> bool:
        if not isinstance(other, (MessageChain, list)):
            return False
        if not isinstance(other, MessageChain):
            other = MessageChain(other)
        return other.as_sendable().content == self.as_sendable().content

    def __add__(self, content: Union[Self, List[Element], Element, str]) -> Self:
        if isinstance(content, str):
            content = Plain(content)
        if isinstance(content, Element):
            content = [content]
        if isinstance(content, MessageChain):
            content = content.content
        return MessageChain(self.content + content, inline=True)

    def __radd__(self, content: Union[Self, List[Element], Element, str]) -> Self:
        if isinstance(content, str):
            content = Plain(content)
        if isinstance(content, Element):
            content = [content]
        if isinstance(content, MessageChain):
            content = content.content
        return MessageChain(content + self.content, inline=True)

    def __iadd__(self, content: Union[Self, List[Element], Element, str]) -> Self:
        if isinstance(content, str):
            content = Plain(content)
        if isinstance(content, Element):
            content = [content]
        if isinstance(content, MessageChain):
            content = content.content
        self.content.extend(content)
        return self

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

    def __iter__(self) -> Iterator[Element]:
        yield from self.content

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
                result.append(element_cls.parse_obj(Json.deserialize(j_string)))
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
        for x in re.split("(\x02\\d+_\\w+\x03)", string):
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
            skip_header (bool, optional): 是否要忽略 Source 与 Quote 类型查找, 默认为 True. (移除后仍会带上 Source 与 Quote)

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
        old: "Self | Iterable[Element] | Element",
        new: "Self | Iterable[Element] | Element",
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
        index_list: List[int] = self.find_sub_chain(old)
        unzipped_new: List[Union[str, Element]] = new.unzip()
        unzipped_old: List[Union[str, Element]] = old.unzip()
        unzipped_self: List[Union[str, Element]] = self.unzip()
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

    if not TYPE_CHECKING:

        @classmethod
        @deprecated("0.8.0", "Instantiate `MessageChain` directly instead.")
        def create(cls, *elements: Union[Iterable[Element], Element, str]) -> Self:
            """
            创建消息链.

            Args:
                *elements (Union[Iterable[Element], Element, str]): \
                元素的容器, 为承载元素的可迭代对象/单元素实例, \
                字符串会被自动不可逆的转换为 `Plain`

            Returns:
                MessageChain: 创建的消息链
            """

            return cls(*elements)

        @deprecated("0.8.0", "Use `as_sendable` instead.")
        def prepare(self, copy: bool = False) -> Self:
            """
            对消息链中所有元素进行处理.

            Returns:
                MessageChain: copy = True 时返回副本, 否则返回自己的引用.
            """
            return self.as_sendable()

        @deprecated("0.8.0", "Use `display` instead.")
        def as_display(self) -> str:
            """
            获取以字符串形式表示的消息链, 且趋于通常你见到的样子.

            Returns:
                str: 以字符串形式表示的消息链
            """
            return "".join(i.display for i in self.content)

        @deprecated("0.8.0", "Use `only` instead.")
        def only_contains(self, *types: Type[Element]) -> bool:
            """判断消息链中是否只含有特定类型元素.

            Returns:
                bool: 判断结果
            """
            return self.only(*types)


_update_forward_refs()
