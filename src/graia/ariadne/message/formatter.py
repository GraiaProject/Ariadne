"""基于 format string 的消息链格式化器"""
import re
from typing import Dict, List, Union

from .chain import MessageChain
from .element import Element, Plain


class Formatter:
    """类似于 string.Formatter 的消息链格式化器"""

    format_string: str

    def __init__(self, format_string: str) -> None:
        self.format_string = format_string

    def format(
        self, *o_args: Union[Element, MessageChain, str], **o_kwargs: Union[Element, MessageChain, str]
    ) -> MessageChain:
        """通过初始化时传入的格式字符串 格式化消息链

        Args:
            *o_args (Union[Element, MessageChain, str]): 格式化时传入的关键字参数
            **o_kwargs (Union[Element, MessageChain, str]): 格式化时传入的关键字参数

        Returns:
            MessageChain: 格式化后的消息链
        """
        args: List[MessageChain] = [MessageChain.create(e) for e in o_args]
        kwargs: Dict[str, MessageChain] = {k: MessageChain.create(e) for k, e in o_kwargs.items()}

        args_mapping: Dict[str, MessageChain] = {
            f"\x02{index}\x02": chain for index, chain in enumerate(args)
        }
        kwargs_mapping: Dict[str, MessageChain] = {f"\x03{key}\x03": chain for key, chain in kwargs.items()}

        result = self.format_string.format(*args_mapping, **{k: f"\x03{k}\x03" for k in kwargs})

        chain_list: List[Union[MessageChain, Plain]] = []

        for i in re.split("([\x02\x03][\\d\\w]+[\x02\x03])", result):
            if match := re.fullmatch("(?P<header>[\x02\x03])(?P<content>\\w+)(?P=header)", i):
                header = match.group("header")
                full: str = match.group(0)
                if header == "\x02":  # from args
                    chain_list.append(args_mapping[full])
                else:  # \x03, from kwargs
                    chain_list.append(kwargs_mapping[full])
            else:
                chain_list.append(Plain(i))
        return MessageChain.create(*chain_list).merge()
