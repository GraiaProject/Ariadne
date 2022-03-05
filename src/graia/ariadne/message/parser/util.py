"""消息链处理器用到的工具函数, 类"""
import argparse
import enum
import inspect
import re
from contextvars import ContextVar
from typing import Dict, List, Literal, NoReturn, Tuple, Type, Union

from graia.ariadne.message.element import Element

from ..chain import Element_T, MessageChain

elem_mapping_ctx: ContextVar[Dict[str, Element]] = ContextVar("elem_mapping_ctx")

L_PAREN = ("{", "[")
R_PAREN = ("}", "]")
ESCAPE = {
    "\\": "\x00",
    "[": "\x01",
    "]": "\x02",
    "{": "\x03",
    "}": "\x04",
    "|": "\x05",
}
R_ESCAPE = {v: k for k, v in ESCAPE.items()}


def escape(string: str) -> str:
    """转义字符串

    Args:
        string (str): 要转义的字符串

    Returns:
        str: 转义后的字符串
    """
    for k, v in ESCAPE.items():
        string = string.replace("\\" + k, v)
    string = string.replace("\\", "")
    return string


def unescape(string: str) -> str:
    """逆转义字符串, 自动去除空白符

    Args:
        string (str): 要逆转义的字符串

    Returns:
        str: 逆转义后的字符串
    """
    for k, v in R_ESCAPE.items():
        string = string.replace(k, v)
    return string.strip()


class CommandToken(enum.Enum):
    """Command 的 Token."""

    TEXT = "TEXT"
    CHOICE = "CHOICE"
    PARAM = "PARAM"
    ANNOTATED = "ANNOTATED"


CommandTokenTuple = Union[
    Tuple[Literal[CommandToken.PARAM], List[Union[int, str]]],
    Tuple[Literal[CommandToken.ANNOTATED, CommandToken.CHOICE, CommandToken.PARAM], List[str]],
]


def tokenize_command(string: str) -> List[CommandTokenTuple]:
    """将字符串转义化, 并处理为 Text, Choice, Param, AnnotatedParam 四种 token

    Args:
        string (str): 要处理的字符串

    Returns:
        List[Tuple[CommandToken, List[int, str]]]: 处理后的 Token
    """

    string = escape(string)

    paren: str = ""
    char_stk: List[str] = []
    token: List[CommandTokenTuple] = []

    for index, char in enumerate(string):
        if char in L_PAREN + R_PAREN:
            if char in L_PAREN:
                if paren:
                    raise ValueError(
                        f"""Duplicated parenthesis character "{char}" @ {index} !"""
                        """Are you sure you've escaped with "\\"?"""
                    )
                paren = char
            elif char in R_PAREN:
                if paren == "[":  # CHOICE
                    token.append((CommandToken.CHOICE, list(map(unescape, "".join(char_stk).split("|")))))
                elif paren == "{":  # PARAM
                    piece = "".join(char_stk)
                    match = re.fullmatch(
                        r"(?P<wildcard>\.\.\.)?"
                        r"(?P<name>[^:=|]+)"
                        r"(?P<annotation>:[^=]+)?"
                        r"(?P<default>=.+)?",
                        piece,
                    )
                    if match and any(s in piece for s in ".:="):
                        token.append(  # type: List[str]
                            (
                                CommandToken.ANNOTATED,
                                list(
                                    map(
                                        lambda x: unescape(x).strip().lstrip(":=").strip() if x else "",
                                        match.groups(),
                                    )
                                ),
                            )
                        )
                    else:
                        token.append(
                            (
                                CommandToken.PARAM,
                                [
                                    int(i) if re.match(r"\d+", i) else unescape(i)
                                    for i in "".join(char_stk).split("|")
                                ],
                            )
                        )
                else:
                    raise ValueError(f"No matching parenthesis: {paren} @ {index}")
                char_stk.clear()
                paren = ""
            char_stk.clear()
        elif char == " " and not paren:
            if char_stk:
                token.append((CommandToken.TEXT, ["".join(char_stk)]))
                char_stk.clear()
        else:
            char_stk.append(char)

    if paren:
        raise ValueError(f"Unclosed parenthesis: {paren}")

    if char_stk:
        token.append((CommandToken.TEXT, ["".join(char_stk)]))
        char_stk.clear()

    return token


def split(string: str, keep_quote: bool = False) -> List[str]:
    """尊重引号与转义的字符串切分

    Args:
        string (str): 要切割的字符串
        keep_quote (bool): 是否保留引号, 默认 False.

    Returns:
        List[str]: 切割后的字符串, 可能含有空格
    """
    result: List[str] = []
    quote = ""
    cache: List[str] = []
    for index, char in enumerate(string):
        if char in {"'", '"'}:
            if not quote:
                quote = char
            elif char == quote and index and string[index - 1] != "\\":  # is current quote, not transfigured
                quote = ""
            else:
                cache.append(char)
                continue
            if keep_quote:
                cache.append(char)
        elif not quote and char == " ":
            result.append("".join(cache))
            cache = []
        elif char != "\\":
            cache.append(char)
    if cache:
        result.append("".join(cache))
    return result


def gen_flags_repr(flags: re.RegexFlag) -> str:
    """通过 RegexFlag 生成对应的字符串

    Args:
        flags (re.RegexFlag): 正则表达式的标记

    Returns:
        str: 对应的标记字符串
    """
    flags_list: List[str] = []

    if re.ASCII in flags:
        flags_list.append("a")
    if re.IGNORECASE in flags:
        flags_list.append("i")
    if re.LOCALE in flags:
        flags_list.append("L")
    if re.MULTILINE in flags:
        flags_list.append("m")
    if re.DOTALL in flags:
        flags_list.append("s")
    if re.UNICODE in flags:
        flags_list.append("u")
    if re.VERBOSE in flags:
        flags_list.append("x")

    return "".join(flags_list)


def transform_regex(flag: re.RegexFlag, regex_pattern: str) -> str:
    """生成嵌套正则表达式字符串来达到至少最外层含有一个捕获组的效果

    Args:
        flag (re.RegexFlag): 正则表达式标记
        regex_pattern (str): 正则表达式字符串

    Returns:
        str: 转换后的正则表达式字符串
    """
    if flag:
        regex_pattern = f"(?{gen_flags_repr(flag)}:({regex_pattern}))"
    else:
        regex_pattern = f"({regex_pattern})"
    return regex_pattern


class MessageChainType:
    """用于标记类型为消息链, 在 ArgumentMatch 上使用"""

    @staticmethod
    def __call__(string: str) -> MessageChain:
        return MessageChain._from_mapping_string(string, elem_mapping_ctx.get())


class ElementType:
    """用于标记类型为消息链元素, 在 ArgumentMatch 上使用"""

    def __init__(self, pattern: Type[Element_T]):
        self.regex = re.compile(f"\x02(\\d+)_{pattern.__fields__['type'].default}\x03")

    def __call__(self, string: str) -> MessageChain:
        if not self.regex.fullmatch(string):
            raise ValueError(f"{string} not matching {self.regex.pattern}")
        return MessageChain._from_mapping_string(string, elem_mapping_ctx.get())[0]


class UnmatchedClass:
    __slots__ = ()

    def __repr__(self) -> str:
        return "<Unmatched>"

    def __bool__(self) -> bool:
        return False


Unmatched = UnmatchedClass()


class TwilightParser(argparse.ArgumentParser):
    """适于 Twilight 使用的 argparse.ArgumentParser 子类
    移除了报错时自动退出解释器的行为
    """

    def error(self, message) -> NoReturn:
        raise ValueError(message)

    def accept_type(self, action: Union[str, type]) -> bool:
        """检查一个 action 是否接受 type 参数

        Args:
            action (Union[str, type]): 检查的 action

        Returns:
            bool: 是否接受 type 参数
        """
        if action is ...:
            action = "store"
        if isinstance(action, str):
            action_cls: Type[argparse.Action] = self._registry_get("action", action, action)
        elif isinstance(action, type) and issubclass(action, argparse.Action):
            action_cls = action
        else:
            return False
        action_init_sig = inspect.signature(action_cls.__init__)
        if "type" not in action_init_sig.parameters:
            return False
        return True
