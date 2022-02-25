"""Ariadne 消息链的实现"""
import json
import re
from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

from ..model import AriadneBaseModel
from ..util import gen_subclass
from .element import (
    At,
    AtAll,
    Element,
    File,
    MultimediaElement,
    NotSendableElement,
    Plain,
    Quote,
    Source,
    _update_forward_refs,
)

if TYPE_CHECKING:
    from ..typing import MessageIndex, ReprArgs, Slice


Element_T = TypeVar("Element_T", bound=Element)

ELEMENT_MAPPING: Dict[str, Type[Element]] = {
    i.__fields__["type"].default: i for i in gen_subclass(Element) if hasattr(i.__fields__["type"], "default")
}


class MessageChain(AriadneBaseModel):
    """
    即 "消息链", 被用于承载整个消息内容的数据结构, 包含有一有序列表, 包含有元素实例.
    """

    __root__: List[Element]
    """底层元素列表"""

    @staticmethod
    def build_chain(obj: List[Union[dict, Element, str]]) -> List[Element]:
        """内部接口, 会自动反序列化对象并生成.

        Args:
            obj (List[T]): 需要反序列化的对象

        Returns:
            List[Element]: 内部承载有尽量有效的消息元素的列表
        """
        element_list: List[Element] = []
        for i in obj:
            if isinstance(i, Element):
                element_list.append(i)
            elif isinstance(i, dict) and "type" in i:
                for element_cls in gen_subclass(Element):
                    if element_cls.__name__ == i["type"]:
                        element_list.append(element_cls.parse_obj(i))
                        break
            elif isinstance(i, str):
                element_list.append(Plain(i))
        return element_list

    @classmethod
    def parse_obj(cls: Type["MessageChain"], obj: List[Union[dict, Element]]) -> "MessageChain":
        """内部接口, 会自动将作为外部态的消息元素转为内部态.

        Args:
            obj (List[T]): 需要反序列化的对象

        Returns:
            MessageChain: 内部承载有尽量有效的消息元素的消息链
        """
        return cls(__root__=cls.build_chain(obj))

    def __init__(
        self,
        __root__: Iterable[Union[Element, str]],
        inline: bool = False,
    ) -> None:
        if not inline:
            super().__init__(__root__=self.build_chain(__root__))
        else:
            super().__init__(__root__=__root__)

    @classmethod
    def create(cls, *elements: Union[Iterable[Element], Element, str]) -> "MessageChain":
        """
        创建消息链.
        比起直接实例化, 本方法拥有更丰富的输入实例类型支持.

        Args:
            *elements(Union[Iterable[Element], Element, str]): 元素的容器, \
            为承载元素的可迭代对象/单元素实例, \
            字符串会被自动不可逆的转换为 `Plain`

        Returns:
            MessageChain: 创建的消息链
        """

        element_list = []
        for i in elements:
            if isinstance(i, Element):
                element_list.append(i)
            elif isinstance(i, str):
                element_list.append(Plain(i))
            else:
                element_list.extend(cls.build_chain(i))
        return cls(__root__=element_list, inline=True)

    def prepare(self, copy: bool = False) -> "MessageChain":
        """
        对消息链中所有元素进行处理.

        Returns:
            MessageChain: copy = True 时返回副本, 否则返回自己的引用.
        """
        chain_ref = self.copy() if copy else self
        chain_ref.merge()
        for i in chain_ref.__root__[:]:
            try:
                i.prepare()
            except NotSendableElement:
                chain_ref.__root__.remove(i)
        return chain_ref

    def unzip(self) -> List[Union[str, Element]]:
        """解压消息链为元素/单字符列表.
        Args:
            self (MessageChain): 消息链.
        Return:
            List[Union[str, Element]]: 解压后的元素/字符列表.
        """
        unzipped: List[Union[str, Element]] = []
        for e in self.__root__:
            if isinstance(e, Plain):
                unzipped.extend(e.text)
            else:
                unzipped.append(e)
        return unzipped

    def has(self, item: Union[Element, Type[Element], "MessageChain", str]) -> bool:
        """
        判断消息链中是否含有特定的元素/元素类型/消息链/字符串.

        Args:
            item (Union[Element_T, Type[Element_T], "MessageChain"]): 需要判断的元素/元素类型/消息链/字符串.

        Returns:
            bool: 判断结果
        """
        if isinstance(item, str):
            return bool(self.findSubChain(MessageChain([Plain(item)], inline=True)))
        if isinstance(item, Element):
            return item in self.merge(copy=True).__root__
        if isinstance(item, type):
            return item in [type(i) for i in self.__root__]
        if isinstance(item, MessageChain):
            return bool(self.findSubChain(item))
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
            count = len(self.__root__)
        return [i for i in self.__root__ if isinstance(i, element_class)][:count]

    def getOne(self, element_class: Type[Element_T], index: int) -> Element_T:
        """
        获取消息链中第 index + 1 个特定类型的消息元素

        Args:
            element_class (Type[Element_T]): 指定的消息元素的类型, 例如 "Plain", "At", "Image" 等.
            index (int): 索引, 从 0 开始数

        Returns:
            Element_T: 消息链第 index + 1 个特定类型的消息元素
        """
        return self.get(element_class)[index]

    def getFirst(self, element_class: Type[Element_T]) -> Element_T:
        """
        获取消息链中第 1 个特定类型的消息元素

        Args:
            element_class (Type[Element_T]): 指定的消息元素的类型, 例如 "Plain", "At", "Image" 等.

        Returns:
            Element_T: 消息链第 1 个特定类型的消息元素
        """
        return self.getOne(element_class, 0)

    def asDisplay(self) -> str:
        """
        获取以字符串形式表示的消息链, 且趋于通常你见到的样子.

        Returns:
            str: 以字符串形式表示的消息链
        """
        return "".join(i.asDisplay() for i in self.__root__)

    def __str__(self) -> str:
        return self.asDisplay()

    def __repr_args__(self) -> "ReprArgs":
        return [(None, list(self.__root__))]

    def __contains__(self, item: Union["MessageChain", Type[Element_T], Element_T, str]) -> bool:
        """
        是否包含特定对象
        """
        return self.has(item)

    @overload
    def __getitem__(self, item: Tuple[Element_T, int]) -> List[Element_T]:
        ...

    @overload
    def __getitem__(self, item: Type[Element_T]) -> List[Element_T]:
        ...

    @overload
    def __getitem__(self, item: int) -> Element_T:
        ...

    @overload
    def __getitem__(self, item: slice) -> "MessageChain":
        ...

    def __getitem__(
        self, item: Union[Type[Element_T], slice, Tuple[Type[Element_T], int], int]
    ) -> Union[List[Element_T], "MessageChain", Element]:
        """
        可通过切片取出子消息链, 或元素.

        通过 `type, count` 型元组取出前 `count` 个 `type` 元素组成的列表

        通过 `type` 取出属于 `type` 的元素列表

        通过 `int` 取出对应位置元素.

        Args:
            item: 索引项
        Returns:
            索引结果.
        """
        if isinstance(item, slice):
            return self.subchain(item)
        if isinstance(item, type) and issubclass(item, Element):
            return self.get(item)
        if isinstance(item, tuple):
            return self.get(*item)
        if isinstance(item, int):
            return self.__root__[item]
        raise NotImplementedError(f"{item} is not allowed for item getting")

    def subchain(
        self,
        item: "Slice[Optional[MessageIndex], Optional[MessageIndex]]",
        ignore_text_index: bool = False,
    ) -> "MessageChain":
        """对消息链执行分片操作

        Args:
            item (slice): 这个分片的 `start` 和 `end` 的 Type Annotation 都是 `Optional[MessageIndex]`
            ignore_text_index (bool, optional): 在 TextIndex 取到错误位置时是否引发错误.

        Raises:
            ValueError: TextIndex 取到了错误的位置

        Returns:
            MessageChain: 分片后得到的新消息链, 绝对是原消息链的子集.
        """
        if isinstance(item.start, int) and isinstance(item.stop, int):
            return MessageChain(self.__root__[item], inline=True)
        result = self.merge(copy=True).__root__[
            item.start[0] if item.start else None : item.stop[0] if item.stop else None
        ]
        if len(result) == 1:
            text_start: Optional[int] = (
                item.start[1]
                if item.start and len(item.start) >= 2 and isinstance(item.start[1], int)
                else None
            )
            text_stop: Optional[int] = (
                item.stop[1] if item.stop and len(item.stop) >= 2 and isinstance(item.stop[1], int) else None
            )
            elem = result[0]
            if not isinstance(elem, Plain):
                if not ignore_text_index:
                    raise ValueError(f"the sliced chain does not starts with a Plain: {elem}")
            else:
                elem.text = elem.text[text_start:text_stop]
        elif len(result) >= 2:
            if item.start:
                first_element = result[0]
                if len(item.start) >= 2 and item.start[1] is not None:  # text slice
                    if not isinstance(first_element, Plain):
                        if not ignore_text_index:
                            raise ValueError(
                                f"the sliced chain does not starts with a Plain: {first_element}"
                            )
                    else:
                        first_element.text = first_element.text[item.start[1] :]
            if item.stop:
                last_element = result[-1]
                if len(item.stop) >= 2 and item.stop[1] is not None:  # text slice
                    if not isinstance(last_element, Plain):
                        if not ignore_text_index:
                            raise ValueError(f"the sliced chain does not ends with a Plain: {last_element}")
                    else:
                        last_element.text = last_element.text[: item.stop[1]]

        return MessageChain(result, inline=True)

    def findSubChain(self, subchain: Union["MessageChain", List[Element]]) -> List[int]:
        """判断消息链是否含有子链. 使用 KMP 算法.

        Args:
            chain (Union[MessageChain, List[Element]]): 要判断的子链.

        Returns:
            List[int]: 所有找到的下标.
        """
        pattern: List[Union[str, Element]] = subchain.unzip()

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

    def exclude(self, *types: Type[Element]) -> "MessageChain":
        """将除了在给出的消息元素类型中符合的消息元素重新包装为一个新的消息链

        Args:
            *types (Type[Element]): 将排除在外的消息元素类型

        Returns:
            MessageChain: 返回的消息链中不包含参数中给出的消息元素类型
        """
        return MessageChain([i for i in self.copy().__root__ if type(i) not in types], inline=True)

    def include(self, *types: Type[Element]) -> "MessageChain":
        """将只在给出的消息元素类型中符合的消息元素重新包装为一个新的消息链

        Args:
            *types (Type[Un]): 将只包含在内的消息元素类型

        Returns:
            MessageChain: 返回的消息链中只包含参数中给出的消息元素类型
        """
        return MessageChain([i for i in self.copy().__root__ if type(i) in types], inline=True)

    def split(self, pattern: str = " ", raw_string: bool = False) -> List["MessageChain"]:
        """和 `str.split` 差不多, 提供一个字符串, 然后返回分割结果.

        Args:
            pattern (str): 分隔符. 默认为单个空格.
            raw_string (bool): 是否要包含 "空" 的文本元素.

        Returns:
            List["MessageChain"]: 分割结果, 行为和 `str.split` 差不多.
        """

        result: List["MessageChain"] = []
        tmp = []
        for element in self.__root__:
            if isinstance(element, Plain):
                split_result = element.text.split(pattern)
                for index, split_str in enumerate(split_result):
                    if tmp and index > 0:
                        result.append(MessageChain(tmp, inline=True))
                        tmp = []
                    if split_str or raw_string:
                        tmp.append(Plain(split_str))
            else:
                tmp.append(element)

        if tmp:
            result.append(MessageChain(tmp, inline=True))
            tmp = []

        return result

    def __iter__(self) -> Iterator[Element]:
        return iter(self.__root__)

    def startswith(self, string: str, ignore_header: bool = True) -> bool:
        """
        判定消息链是否以相应字符串开头

        Args:
            string (str): 需要判断的字符串
            ignore_header (bool, optional): 是否忽略元数据, 默认为 True

        Returns:
            bool: 是否以此字符串开头
        """

        ref_root = self.asSendable().__root__ if ignore_header else self.__root__

        if not ref_root or not isinstance(ref_root[0], Plain):
            return False
        return ref_root[0].text.startswith(string)

    def endswith(self, string: str) -> bool:
        """
        判定消息链是否以相应字符串结尾

        Args:
            string (str): 需要判断的字符串

        Returns:
            bool: 是否以此字符串结尾
        """

        if not self.__root__ or not isinstance(self.__root__[-1], Plain):
            return False
        last_element: Plain = self.__root__[-1]
        return last_element.text.endswith(string)

    def onlyContains(self, *types: Type[Element]) -> bool:
        """判断消息链中是否只含有特定类型元素.

        Returns:
            bool: 判断结果
        """
        return all(isinstance(i, types) for i in self.__root__)

    def merge(self, copy: bool = False) -> "MessageChain":
        """
        在实例内合并相邻的 Plain 项

        copy (bool): 是否要在副本上修改.
        Returns:
            MessageChain: copy = True 时返回副本, 否则返回自己的引用.
        """

        result = []

        plain = []
        for i in self.__root__:
            if not isinstance(i, Plain):
                if plain:
                    result.append(Plain("".join(plain)))
                    plain.clear()  # 清空缓存
                result.append(deepcopy(i) if copy else i)
            else:
                plain.append(i.text)

        if plain:
            result.append(Plain("".join(plain)))
            plain.clear()

        if copy:
            return MessageChain(result, inline=True)
        self.__root__ = result
        return self

    def append(self, element: Union[Element, str], copy: bool = False) -> "MessageChain":
        """
        向消息链最后追加单个元素

        Args:
            element (Element): 要添加的元素
            copy (bool): 是否要在副本上修改.

        Returns:
            MessageChain: copy = True 时返回副本, 否则返回自己的引用.
        """
        chain_ref = self.copy() if copy else self
        if isinstance(element, str):
            element = Plain(element)
        chain_ref.__root__.append(element)
        return chain_ref

    def extend(
        self,
        *content: Union["MessageChain", Element, List[Union[Element, str]]],
        copy: bool = False,
    ) -> "MessageChain":
        """
        向消息链最后添加元素/元素列表/消息链

        Args:
            *content (Union[MessageChain, Element, List[Element]]): 要添加的元素/元素容器.
            copy (bool): 是否要在副本上修改.

        Returns:
            MessageChain: copy = True 时返回副本, 否则返回自己的引用.
        """
        result = []
        for i in content:
            if isinstance(i, Element):
                result.append(i)
            elif isinstance(i, str):
                result.append(Plain(i))
            elif isinstance(i, MessageChain):
                result.extend(i.__root__)
            else:
                for e in i:
                    if isinstance(e, str):
                        result.append(Plain(e))
                    else:
                        result.append(e)
        if copy:
            return MessageChain(deepcopy(self.__root__) + result, inline=True)
        self.__root__.extend(result)
        return self

    def copy(self) -> "MessageChain":
        """
        拷贝本消息链.

        Returns:
            MessageChain: 拷贝的副本.
        """
        return MessageChain(deepcopy(self.__root__), inline=True)

    def index(self, element_type: Type[Element_T]) -> Union[int, None]:
        """
        寻找第一个特定类型的元素, 并返回其下标.

        Args:
            element_type (Type[Element]): 元素或元素类型

        Returns:
            Optional[int]: 元素下标, 若未找到则为 None.

        """
        for i, e in enumerate(self.__root__):
            if isinstance(e, element_type):
                return i
        return None

    def count(self, element: Union[Type[Element_T], Element_T]) -> int:
        """
        统计共有多少个指定的元素.

        Args:
            element (Type[Element] | Element): 元素或元素类型

        Returns:
            int: 元素数量
        """
        if isinstance(element, Element):
            return sum(i == element for i in self.__root__)
        return sum(isinstance(i, element) for i in self.__root__)

    def asSendable(self) -> "MessageChain":
        """将消息链转换为可发送形式 (去除 Source, Quote, File)

        Returns:
            MessageChain: 转换后的消息链.
        """
        return self.exclude(Source, Quote, File)

    def __eq__(self, other: Union[List[Union[Element, str]], "MessageChain"]) -> bool:
        if not isinstance(other, (list, MessageChain)):
            return False
        if isinstance(other, list):
            other = MessageChain(other)
        return other.asSendable().__root__ == self.asSendable().__root__

    def __add__(self, content: Union["MessageChain", List[Element], Element, str]) -> "MessageChain":
        if isinstance(content, str):
            content = Plain(content)
        if isinstance(content, Element):
            content = [content]
        if isinstance(content, MessageChain):
            content: List[Element] = content.__root__
        return MessageChain(self.__root__ + content, inline=True)

    def __radd__(self, content: Union["MessageChain", List[Element], Element, str]) -> "MessageChain":
        if isinstance(content, str):
            content = Plain(content)
        if isinstance(content, Element):
            content = [content]
        if isinstance(content, MessageChain):
            content: List[Element] = content.__root__
        return MessageChain(content + self.__root__, inline=True)

    def __iadd__(self, content: Union["MessageChain", List[Element], Element, str]) -> "MessageChain":
        if isinstance(content, str):
            content = Plain(content)
        if isinstance(content, Element):
            content = [content]
        if isinstance(content, MessageChain):
            content: List[Element] = content.__root__
        self.__root__.extend(content)
        return self

    def __mul__(self, time: int) -> "MessageChain":
        result = []
        for _ in range(time):
            result.extend(deepcopy(self.__root__))
        return MessageChain(result, inline=True)

    def __imul__(self, time: int) -> "MessageChain":
        self.__root__ = self.__mul__(time).__root__
        return self

    def __len__(self) -> int:
        return len(self.__root__)

    def asPersistentString(
        self,
        *,
        binary: bool = True,
        include: Optional[Iterable[Type[Element]]] = (),
        exclude: Optional[Iterable[Type[Element]]] = (),
    ) -> str:
        """转换为持久化字符串.

        Args:
            binary (bool, optional): 是否附带图片或声音的二进制. 默认为 True.
            include (Optional[Iterable[Type[Element]]], optional): 筛选, 只包含本参数提供的元素类型.
            exclude (Optional[Iterable[Type[Element]]], optional): 筛选, 排除本参数提供的元素类型.

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
        for i in self.__root__:
            if (
                (include and isinstance(i, include))
                or (exclude and not isinstance(i, exclude))
                or not (include or exclude)
            ):
                if isinstance(i, Plain):
                    string_list.append(i.asPersistentString().replace("[", "[_"))
                elif not isinstance(i, MultimediaElement) or binary:
                    string_list.append(i.asPersistentString())
                else:
                    string_list.append(i.asNoBinaryPersistentString())
        return "".join(string_list)

    async def download_binary(self) -> None:
        """下载消息中所有的二进制数据并保存在元素实例内"""
        for elem in self.__root__:
            if isinstance(elem, MultimediaElement):
                await elem.get_bytes()
        return self

    @classmethod
    def fromPersistentString(cls, string: str) -> "MessageChain":
        """从持久化字符串生成消息链.

        Returns:
            MessageChain: 还原的消息链.
        """
        result = []
        for match in re.split(r"(\[mirai:.+?\])", string):
            mirai = re.fullmatch(r"\[mirai:(.+?)(:(.+?))\]", match)
            if mirai:
                j_string = mirai.group(3)
                element_cls = ELEMENT_MAPPING[mirai.group(1)]
                result.append(element_cls.parse_obj(json.loads(j_string)))
            elif match:
                result.append(Plain(match.replace("[_", "[")))
        return MessageChain.create(result)

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
        elem_mapping: Dict[int, Element] = {}
        elem_str_list: List[str] = []
        for i, elem in enumerate(self.__root__):
            if not isinstance(elem, Plain):
                if remove_quote and isinstance(elem, Quote):
                    continue
                if remove_source and isinstance(elem, Source):
                    continue
                elem_mapping[str(i)] = elem
                elem_str_list.append(f"\x02{i}_{elem.type}\x03")
            else:
                if (
                    remove_extra_space
                    and i  # not first element
                    and isinstance(
                        self.__root__[i - 1], (Quote, At, AtAll)
                    )  # following elements which have an dumb trailing space
                    and elem.text.startswith("  ")  # extra space (count >= 2)
                ):
                    elem_str_list.append(elem.text[1:])
                else:
                    elem_str_list.append(elem.text)
        return "".join(elem_str_list), elem_mapping

    @classmethod
    def _from_mapping_string(cls, string: str, mapping: Dict[str, Element]) -> "MessageChain":
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
        chain = cls([], inline=True)
        chain.__root__ = elements
        return chain

    def removeprefix(self, prefix: str, *, copy: bool = True, skip_header: bool = True) -> "MessageChain":
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
            elements = self.__root__[:]
        else:
            for element in self.__root__:
                if isinstance(element, (Quote, Source)):
                    header.append(element)
                else:
                    elements.append(element)
        if copy:
            header = deepcopy(header)
            elements = deepcopy(elements)
        if not elements or not isinstance(elements[0], Plain):
            return self if not copy else self.copy()
        if elements[0].text.startswith(prefix):
            elements[0].text = elements[0].text[len(prefix) :]
        if copy:
            return MessageChain(header + elements, inline=True)
        self.__root__ = header + elements
        return self

    def removesuffix(self, suffix: str, *, copy: bool = True) -> "MessageChain":
        """移除消息链后缀.

        Args:
            prefix (str): 要移除的后缀.
            copy (bool, optional): 是否在副本上修改, 默认为 True.

        Returns:
            MessageChain: 修改后的消息链, 若未移除则原样返回.
        """
        if copy:
            elements = deepcopy(self.__root__)
        else:
            elements = self.__root__
        if not elements or not isinstance(elements[-1], Plain):
            return self if not copy else self.copy()
        last_elem: Plain = elements[-1]
        if last_elem.text.endswith(suffix):
            last_elem.text = last_elem.text[: -len(suffix)]
        if copy:
            return MessageChain(elements, inline=True)
        self.__root__ = elements
        return self

    def join(self, chains: Iterable["MessageChain"], merge: bool = True) -> "MessageChain":
        """将多个消息链连接起来, 并在其中插入自身.

        Args:
            chains (Iterable[MessageChain]): 要连接的消息链.
            merge (bool, optional): 是否合并消息链文本, 默认为 True.

        Returns:
            MessageChain: 连接后的消息链.
        """
        result: List[Element] = []
        for chain in chains:
            if chain is not chains[0]:
                result.extend(deepcopy(self.__root__))
            result.extend(deepcopy(chain.__root__))
        return MessageChain(result, inline=True) if not merge else MessageChain(result, inline=True).merge()

    def replace(
        self,
        old: "MessageChain | Iterable[Element] | Element",
        new: "MessageChain | Iterable[Element] | Element",
    ) -> "MessageChain":
        """替换消息链中的一部分. (在副本上操作)

        Args:
            old (MessageChain): 要替换的消息链.
            new (MessageChain): 替换后的消息链.

        Returns:
            MessageChain: 修改后的消息链, 若未替换则原样返回.
        """
        if not isinstance(old, MessageChain):
            old = MessageChain.create(old)
        if not isinstance(new, MessageChain):
            new = MessageChain.create(new)
        index_list: List[int] = self.findSubChain(old)
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


_update_forward_refs()
