import argparse
import inspect
import re
from contextvars import ContextVar
from typing import TYPE_CHECKING, List, NoReturn, Type, Union

from ..chain import Element_T, MessageChain

if TYPE_CHECKING:
    from .pattern import ArgumentMatch

elem_mapping_ctx: ContextVar["MessageChain"] = ContextVar("elem_mapping_ctx")


def split(string: str) -> List[str]:
    result: List[str] = []
    quote = ""
    cache: List[str] = []
    for index, char in enumerate(string):
        if char in "'\"":
            if not quote:
                quote = char
            elif char == quote and index and string[index - 1] != "\\":  # is current quote, not transfigured
                quote = ""
            else:
                cache.append(char)
            continue
        if not quote and char == " ":
            result.append("".join(cache))
            cache = []
        else:
            if char != "\\":
                cache.append(char)
    if cache:
        result.append("".join(cache))
    return result


def gen_flags_repr(flags: re.RegexFlag) -> str:
    flags_list: List[str] = []
    if re.ASCII in flags:
        flags_list.append("a")
    if re.IGNORECASE in flags_list:
        flags_list.append("i")
    if re.LOCALE in flags_list:
        flags_list.append("L")
    if re.MULTILINE in flags_list:
        flags_list.append("m")
    if re.DOTALL in flags_list:
        flags_list.append("s")
    if re.UNICODE in flags_list:
        flags_list.append("u")
    if re.VERBOSE in flags_list:
        flags_list.append("x")


class MessageChainType:
    def __init__(self, match: "ArgumentMatch", regex: re.Pattern):
        self.match = match
        self.regex: re.Pattern = regex

    def __call__(self, string: str) -> MessageChain:
        if self.regex and not self.regex.fullmatch(string):
            raise ValueError(f"{string} not matching {self.regex.pattern}")
        return MessageChain.fromMappingString(string, elem_mapping_ctx.get())


class ElementType:
    def __init__(self, match: "ArgumentMatch", pattern: Type[Element_T]):
        self.match = match
        self.regex = re.compile(f"\x02(\\d+)_{pattern.__fields__['type'].default}\x03")

    def __call__(self, string: str) -> MessageChain:
        if not self.regex.fullmatch(string):
            raise ValueError(f"{string} not matching {self.regex.pattern}")
        return MessageChain.fromMappingString(string, elem_mapping_ctx.get())[0]


class TwilightParser(argparse.ArgumentParser):
    def error(self, message) -> NoReturn:
        raise ValueError(message)

    def accept_type(self, action: Union[str, type]) -> bool:
        if isinstance(action, str):
            action_cls: Type[argparse.Action] = self._registry_get("action", action, action)
        elif issubclass(action, argparse.Action):
            action_cls = action
        else:
            return False
        action_init_sig = inspect.signature(action_cls.__init__)
        if "type" not in action_init_sig.parameters:
            return False
        return True
