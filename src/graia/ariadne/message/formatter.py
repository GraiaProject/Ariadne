"""基于 format string 的消息链格式化器"""
from __future__ import annotations

import string
from typing import Any, Literal

from .chain import MessageChain
from .element import Element, Plain

_global_formatter = string.Formatter()


class Formatter:
    """类似于 string.Formatter 的消息链格式化器"""

    format_string: str

    def __init__(self, format_string: str) -> None:
        self.format_string = format_string
        self._fields: tuple[tuple[str, str | None, str | None, str | None], ...] = tuple(
            _global_formatter.parse(format_string)
        )
        for field in self._fields:
            # validation, forbidding the expansion for format spec
            *_, format_spec, _ = field
            if format_spec:
                sub_spec = tuple(_global_formatter.parse(format_spec))
                if len(sub_spec) > 1 or any(sub_spec[1:]):  # Definitely not right spec
                    raise ValueError("Format specification expansion is disallowed, found ")

    @staticmethod
    def _convert_field(value: Any, conversion: None | str) -> Any:
        # do any conversion on the resulting object
        if conversion is None:
            return value
        elif conversion == "s":
            return str(value)
        elif conversion == "r":
            return repr(value)
        elif conversion == "a":
            return ascii(value)
        raise ValueError(f"Unknown conversion specifier {conversion!s}")

    @staticmethod
    def _transform(obj: object) -> list[Element]:
        if isinstance(obj, MessageChain):
            return obj.content
        elif isinstance(obj, (Element, str)):
            return [Plain(obj) if isinstance(obj, str) else obj]
        else:
            return [Plain(str(obj))]

    def format(
        self,
        *args: Element | MessageChain | str | Any,
        **kwargs: Element | MessageChain | str | Any,
    ) -> MessageChain:
        """通过初始化时传入的格式字符串 格式化消息链

        Args:
            *args (Union[Element, MessageChain, str, Any]): 格式化时传入的位置参数
            **kwargs (Union[Element, MessageChain, str, Any]): 格式化时传入的关键字参数

        Returns:
            MessageChain: 格式化后的消息链
        """
        result: list[Element] = []
        auto_arg_index: int | Literal[False] = 0
        used_args: set[str] = set()
        for field in self._fields:
            literal_text, field_name, format_spec, conversion = field
            if literal_text:
                result.append(Plain(literal_text))
            if field_name is None:
                continue
            # if there's a field, output it
            # this is some markup, find the object and do
            #  the formatting

            # handle arg indexing when empty field_names are given.
            if field_name == "":
                if auto_arg_index is False:
                    raise ValueError(
                        "cannot switch from manual field specification to automatic field numbering"
                    )
                field_name = str(auto_arg_index)
                auto_arg_index += 1
            elif field_name.isdigit():
                if auto_arg_index:
                    raise ValueError(
                        "cannot switch from manual field specification to automatic field numbering"
                    )
                # disable auto arg incrementing, if it gets
                # used later on, then an exception will be raised
                auto_arg_index = False

            # given the field_name, find the object it references
            #  and the argument it came from
            obj, arg_used = _global_formatter.get_field(field_name, args, kwargs)
            used_args.add(arg_used)

            # do any conversion on the resulting object
            obj = self._convert_field(obj, conversion)

            # format the object and append to the result
            if format_spec:
                obj = format(obj, format_spec)

            result.extend(self._transform(obj))

        return MessageChain(result, inline=True).merge()
