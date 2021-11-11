import argparse
import inspect
import re
from typing import TYPE_CHECKING, List, NoReturn, Type, Union

from ..chain import MessageChain

if TYPE_CHECKING:
    from .pattern import ArgumentMatch


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


class ArgumentMatchType:
    def __init__(self, match: "ArgumentMatch", regex: re.Pattern):
        self.match = match
        self.regex: re.Pattern = regex

    def __call__(self, string: str) -> MessageChain:
        if self.regex and not self.regex.fullmatch(string):
            raise ValueError(f"{string} not matching {self.regex.pattern}")
        return MessageChain.fromMappingString(string, self.match.elem_mapping_ctx.get())


class TwilightParser(argparse.ArgumentParser):
    def error(self, message) -> NoReturn:
        raise ValueError(message)

    def accept_type(self, action: Union[str, type]) -> bool:
        if isinstance(action, str):
            action_cls: Type[argparse.Action] = self._registry_get(
                "action", action, action
            )
        elif issubclass(action, argparse.Action):
            action_cls = action
        else:
            return False
        action_init_sig = inspect.signature(action_cls.__init__)
        if "type" not in action_init_sig.parameters:
            return False
        return True
