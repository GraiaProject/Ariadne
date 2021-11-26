import re
from typing import Dict, List, Literal, Tuple

from .chain import MessageChain
from .element import Element, Plain


class Formatter:
    format_string: str

    def __init__(self, format_string: str) -> None:
        self.format_string = format_string

    def format(self, *args: Element, **kwargs: Element) -> MessageChain:
        args_mapping: Dict[str, Element] = {
            f"\x02{index}\x02": (element) for index, element in enumerate(args)
        }
        kwargs_mapping: Dict[Tuple[str, str], Element] = {
            (key, f"\x03{key}\x03"): element for key, element in kwargs.items()
        }

        result = self.format_string.format(*args_mapping, **dict(kwargs_mapping.keys()))

        element_list: List[Element] = []

        for i in re.split("([\x02\x03][\\d\\w]+[\x02\x03])", result):
            if match := re.fullmatch(
                "(?P<header>[\x02\x03])(?P<content>\\w+)(?P=header)", i
            ):
                header = match.group("header")
                if header not in ("\x02", "\x03"):
                    raise ValueError(r"Header didn't start with \x02 or \x03!")
                content: str = match.group("content")
                full: str = match.group(0)
                if header == "\x02":  # from args
                    element_list.append(args_mapping[full])
                else:  # \x03, from kwargs
                    element_list.append(kwargs_mapping[(content, full)])
            else:
                element_list.append(Plain(i))
        return MessageChain(element_list, inline=True).merge()
