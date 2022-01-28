"""Commander: 便捷的指令触发体系"""
import abc
import enum
import inspect
import itertools
from contextlib import suppress
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
)

from graia.broadcast import Broadcast
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.exectarget import ExecTarget
from pydantic import BaseModel, create_model, validator
from pydantic.fields import ModelField

from ..dispatcher import ContextDispatcher
from ..model import AriadneBaseModel
from ..util import (
    ConstantDispatcher,
    assert_,
    assert_not_,
    assert_on_,
    const_call,
    eval_ctx,
    resolve_dispatchers_mixin,
)
from .chain import MessageChain
from .element import Element
from .parser.util import CommandToken, CommandTokenTuple, split, tokenize_command

T_Callable = TypeVar("T_Callable", bound=Callable)


def chain_validator(value: MessageChain, field: ModelField) -> Union[MessageChain, Element, str]:
    """
    MessageChain 处理函数.
    应用作 pydantic 的 Model validator.
    取决于字段类型标注, 若与消息链, 消息元素无关则会直接把消息链用 asDisplay 转换为字符串.

    Args:
        value (MessageChain): 消息链
        field (ModelField): 当前的 model 字段

    Returns:
        Union[MessageChain, Element, str]: 取决于字段类型标注
    """
    if field.outer_type_ is MessageChain:
        return value
    if issubclass(field.type_, Element):
        assert len(value) == 1
        assert isinstance(value[0], field.type_)
        return value[0]
    if isinstance(value, MessageChain):
        return value.asDisplay()
    if value is None:
        return field.default
    return value


class ParamDesc(abc.ABC):
    model: Optional[BaseModel]
    default: Any
    default_factory: Callable[[], Any]

    def __or__(self, other: "ParamDesc | Dict[str, Any]"):
        dct = other.__dict__ if isinstance(other, ParamDesc) else other
        for k, v in dct.items():
            if v and v is not ... and not isinstance(v, Decorator):
                self.__dict__[k] = v
        return self

    @abc.abstractmethod
    def gen_model(self, validators: Iterable[Callable]) -> None:
        """生成用于 pydantic 解析的 model 属性

        Args:
            validators (Iterable[Callable]): 用作 validator 的 Callable 可迭代对象
        """
        ...


@dataclass
class Slot(ParamDesc):
    """Slot"""

    def __init__(
        self,
        placeholder: Union[str, int],
        type: Type = ...,
        default: Any = ...,
        default_factory: Callable[[], Any] = ...,
    ) -> None:
        self.placeholder = placeholder
        self.type = type
        self.default = default
        self.default_factory = default_factory
        self.param_name: str = ""
        self.model: Optional[BaseModel] = None

    def gen_model(self, validators: Iterable[Callable]) -> None:
        if self.model:
            return

        self.default_factory = const_call(self.default) if self.default is not ... else self.default_factory

        if self.type is ...:
            self.type = MessageChain

        self.model = create_model(
            "SlotModel",
            __validators__={
                f"#validator_{i}#": validator("*", pre=True, allow_reuse=True)(v)
                for i, v in zip(itertools.count(), validators)
            },
            val=(self.type, ...),  # default is handled at exec
        )


class Arg(ParamDesc):
    """Argument"""

    def __init__(
        self,
        pattern: str,
        type: Type[Union[BaseModel, Any]] = ...,
        default: Any = ...,
        default_factory: Callable[[], Any] = ...,
    ) -> None:

        self.pattern: str = pattern
        self.match_patterns: List[str] = []
        self.tags: List[str] = []
        self.default = default
        self.default_factory = default_factory
        self.param_name: Optional[str] = None

        tokens = tokenize_command(pattern)

        assert_(tokens[0][0] in {CommandToken.TEXT, CommandToken.CHOICE}, "Required argument pattern!")

        self.match_patterns = list(map(str, tokens[0][1]))

        for t_type, token_list in tokens[1:]:
            if t_type in {CommandToken.TEXT, CommandToken.CHOICE}:
                raise ValueError(
                    """Argument pattern can only be placed at head. """
                    """Use "{" and "}" for placeholders."""
                )
            if t_type is CommandToken.PARAM:
                if len(token_list) != 1:
                    raise ValueError("Arg doesn't support aliasing!")
                if str(token_list[0]) in self.tags:
                    raise ValueError("Duplicated tag!")
                self.tags.append(str(token_list[0]))

        self.nargs = len(self.tags)
        self.type = type
        self.model: Optional[BaseModel] = None

    def gen_model(self, validators: Iterable[Callable]) -> None:
        if self.model:
            return

        if self.nargs == 0:
            self.type = self.type if self.type is not ... else bool
            if self.default is ... and self.default_factory is ...:
                self.default = False
        elif self.nargs == 1:
            self.type = self.type if self.type is not ... else MessageChain
        self.default_factory = const_call(self.default) if self.default is not ... else self.default_factory

        if (
            isinstance(self.type, type)
            and issubclass(self.type, BaseModel)
            and not issubclass(self.type, AriadneBaseModel)
        ):
            self.model = self.type
            return

        if self.nargs == 0:  # Set default
            self.model = create_model(
                "ArgModel",
                __validators__={
                    f"#validator_{i}#": validator("*", pre=True, allow_reuse=True)(v)
                    for i, v in zip(itertools.count(), validators)
                },
                val=(self.type, ...),
            )
        elif self.nargs == 1:
            self.model = create_model(
                "ArgModel",
                __validators__={
                    f"#validator_{i}#": validator("*", pre=True, allow_reuse=True)(v)
                    for i, v in zip(itertools.count(), validators)
                },
                **{self.tags[0]: (self.type, ...)},
            )

        if self.model is ...:
            raise ValueError(f"You didn't supply a suitable model for {self.param_name}!")


@dataclass
class CommandPattern:
    """命令样式"""

    class ELast(enum.Enum):
        REQUIRED = "required"
        OPTIONAL = "optional"
        WILDCARD = "wildcard"

    token_list: "List[Set[str] | List[int | str]]"
    slot_map: Dict[Union[str, int], Slot]
    arg_map: Dict[str, Arg]
    last: ELast
    wildcard: str = ""


_raw = object()  # wildcard annotation object


class CommandHandler(ExecTarget):
    """Command 的 ExecTarget 对象, 承担了参数提取等任务"""

    def __init__(
        self,
        record: CommandPattern,
        callable: Callable,
        dispatchers: Sequence[BaseDispatcher] = None,
        decorators: Sequence[Decorator] = None,
    ):
        super().__init__(
            callable,
            [ConstantDispatcher({}), ContextDispatcher(), *resolve_dispatchers_mixin(dispatchers or [])],
            list(decorators),
        )
        self.pattern: CommandPattern = record

    def set_data(
        self,
        slot_data: Dict[Union[int, str], MessageChain],
        arg_data: Dict[str, List[MessageChain]],
        wildcard_chains: List[MessageChain],
    ):
        """基于 CommandRecord 与解析数据设置 ConstantDispatcher 参数

        Args:
            slot_data (Dict[Union[int, str], MessageChain]): Slot 的解析结果
            arg_data (Dict[str, List[MessageChain]]): Arg 的解析结果

        Raises:
            RuntimeError: ConstantDispatcher 被移除了
        """
        param_result: Dict[str, Any] = {}
        for arg in set(self.pattern.arg_map.values()):
            value = arg.default_factory()
            if arg.nargs:
                for param in arg.match_patterns:
                    if param in arg_data:
                        value = dict(zip(arg.tags, arg_data[param]))
                        break
                else:
                    if issubclass(arg.type, BaseModel) and isinstance(value, arg.type):
                        param_result[arg.param_name] = value
                        continue
                    if not isinstance(value, list):
                        value = [value]
                    if not isinstance(value, dict):
                        value = dict(zip(arg.tags, value))

                if not issubclass(arg.type, BaseModel) or issubclass(arg.type, AriadneBaseModel):
                    param_result[arg.param_name] = arg.model(**value).__dict__[arg.tags[0]]
                else:
                    param_result[arg.param_name] = arg.model(**value)

            else:
                if any(param in arg_data for param in arg.match_patterns):
                    value = not value
                param_result[arg.param_name] = arg.model(val=value).__dict__["val"]

        for ind, slot in self.pattern.slot_map.items():
            if slot.param_name != self.pattern.wildcard:
                value = slot_data.get(ind, None) or slot.default_factory()
                param_result[slot.param_name] = slot.model(val=value).__dict__["val"]
            else:
                if slot.type is _raw:
                    param_result[slot.param_name] = MessageChain([" "]).join(wildcard_chains)
                else:
                    param_result[slot.param_name] = tuple(
                        slot.model(val=chain).__dict__["val"] for chain in wildcard_chains
                    )
        if isinstance(self.dispatchers[0], ConstantDispatcher):
            self.dispatchers[0].data = param_result
        else:
            raise RuntimeError("ConstantDispatcher is removed!")


class Commander:
    """便利的指令触发体系"""

    def __init__(self, broadcast: Broadcast):
        self.broadcast = broadcast
        self.command_handlers: List[CommandHandler] = []
        self.validators: List[Callable] = [chain_validator]

    def add_type_cast(self, *caster: Callable):
        """添加类型验证器 (type caster / validator)"""
        self.validators = [*reversed(caster), *self.validators]

    def command(
        self,
        command: str,
        setting: Dict[str, Union[Slot, Arg]] = None,
        dispatchers: Sequence[BaseDispatcher] = (),
        decorators: Sequence[Decorator] = (),
    ) -> Callable[[T_Callable], T_Callable]:
        """装饰一个命令处理函数

        Args:
            command (str): 要处理的命令
            setting (Dict[str, Union[Slot, Arg]], optional): 参数名 -> Slot | Arg 映射, 用于分配参数, 可从函数中推断 `Slot`.
            dispatchers (Sequence[BaseDispatcher], optional): 附加的 `Dispatcher` 序列.
            decorators (Sequence[Decorator], optional): 附加的 `Headless Decorator` 序列.

        Raises:
            ValueError: 在将非最后一个参数设置为可选

        Returns:
            Callable[[T_Callable], T_Callable]: 装饰器
        """

        slot_map: Dict[Union[int, str], Slot] = {}
        pattern_arg_map: Dict[str, Arg] = {}
        param_arg_map: Dict[str, Arg] = {}
        for name, val in (setting or {}).items():
            if isinstance(val, Slot):
                slot_map[val.placeholder] = val
            elif isinstance(val, Arg):
                for pattern in val.match_patterns:
                    pattern_arg_map[pattern] = val
                param_arg_map[name] = val
            else:
                raise TypeError(f"Unknown setting value: {name} - {val!r}")
            val.param_name = name

        token_list: "List[Set[str] | List[int | str]]" = []  # set: const, list: param

        placeholder_set: Set[Union[int, str]] = set()

        last: CommandPattern.ELast = CommandPattern.ELast.REQUIRED
        wildcard_slot_name: str = ""

        command_tokens: List[CommandTokenTuple] = tokenize_command(command)

        for (t_type, tokens) in command_tokens:
            if t_type in {CommandToken.TEXT, CommandToken.CHOICE}:
                assert_not_(
                    any(token in pattern_arg_map for token in tokens),
                    f"{tokens} conflicts with a Arg object!",
                )
                token_list.append(set(cast(List[str], tokens)))

            elif t_type is CommandToken.ANNOTATED:
                wildcard, name, annotation, default = cast(List[str], tokens)
                assert_on_(
                    wildcard or default,
                    tokens is command_tokens[-1][1],
                    "Not setting wildcard / optional on the last slot!",
                )
                if wildcard:
                    last = CommandPattern.ELast.WILDCARD
                if default:
                    last = CommandPattern.ELast.OPTIONAL
                assert_not_(name in placeholder_set, "Duplicated parameter slot!")
                placeholder_set.add(name)
                eval_global, eval_local = eval_ctx(1)
                if wildcard:
                    eval_global = eval_global.copy()
                    eval_global.update(raw=_raw)
                parsed_slot = Slot(
                    name,
                    eval(annotation or "...", eval_global, eval_local),
                    eval(default or "...", eval_global, eval_local),
                )
                parsed_slot.param_name = name  # assuming that param_name is consistent
                slot_map[name] = parsed_slot | slot_map.get(name, {})  # parsed slot < provided slot
                if wildcard:
                    wildcard_slot_name = name
                token_list.append(tokens)
            elif t_type is CommandToken.PARAM:
                for param_name in tokens:
                    assert_not_(param_name in placeholder_set, "Duplicated parameter slot!")
                    placeholder_set.add(param_name)
                token_list.append(tokens)

        def wrapper(func: T_Callable) -> T_Callable:
            """register as command executor"""

            # scan function signature

            def __translate_obj(obj):
                if obj is inspect.Parameter.empty:
                    return ...
                if isinstance(obj, Decorator):
                    return ...
                return obj

            for name, parameter in inspect.signature(func).parameters.items():
                annotation, default = __translate_obj(parameter.annotation), __translate_obj(
                    parameter.default
                )
                if name in placeholder_set:
                    parsed_slot = Slot(name, annotation, default)
                    parsed_slot.param_name = name  # assuming that param_name is consistent
                    slot_map[name] = parsed_slot | slot_map.get(name, {})  # parsed slot < provided slot
                    if default is not ...:
                        assert_(
                            slot_map[name].placeholder in token_list[-1][1]
                            and token_list[-1][0] in {CommandToken.ANNOTATED, CommandToken.PARAM},
                            "Not setting wildcard / optional on the last slot!",
                        )
                        nonlocal last
                        if last is CommandPattern.ELast.REQUIRED:
                            last = CommandPattern.ELast.OPTIONAL

                if name in param_arg_map:
                    arg = param_arg_map[name]
                    arg.type = arg.type if arg.type is not ... else parameter.annotation
                    if arg.default is ... and arg.default_factory is ...:
                        arg.default = parameter.default

            for slot in slot_map.values():
                slot.gen_model(self.validators)
            for arg in param_arg_map.values():
                arg.gen_model(self.validators)

            self.command_handlers.append(
                CommandHandler(
                    CommandPattern(token_list, slot_map, pattern_arg_map, last, wildcard_slot_name),
                    func,
                    dispatchers,
                    decorators,
                )
            )

            return func

        return wrapper

    async def execute(self, chain: MessageChain):
        """触发 Commander.

        Args:
            chain (MessageChain): 触发的消息链
        """

        mapping_str, elem_m = chain.asMappingString()

        for handler in reversed(self.command_handlers):  # starting from latest added
            with suppress(IndexError, ValueError):
                pattern = handler.pattern
                arg_data: DefaultDict[str, List[MessageChain]] = DefaultDict(list)
                slot_data: Dict[Union[str, int], MessageChain] = {}
                # scan Arg data
                mixed_str = split(mapping_str)
                text_str: List[str] = []
                scan_index: int = 0
                while scan_index < len(mixed_str):
                    current: str = mixed_str[scan_index]
                    scan_index += 1
                    if current not in pattern.arg_map:
                        text_str.append(current)
                    else:
                        assert_not_(current in arg_data, "Duplicated argument.")
                        nargs = pattern.arg_map[current].nargs
                        arg_data[current] = [
                            MessageChain.fromMappingString(piece, elem_m)
                            for piece in mixed_str[scan_index : scan_index + nargs]
                        ]
                        scan_index += nargs
                # scan text + Slot
                for scan_index, tokens in enumerate(pattern.token_list[:-1]):
                    if isinstance(tokens, set) and text_str[scan_index] not in tokens:
                        raise ValueError("Mismatch")
                    elif isinstance(tokens, list):
                        for slot in tokens:
                            slot_data[slot] = MessageChain.fromMappingString(text_str[scan_index], elem_m)
                scan_index += 1
                tokens = pattern.token_list[-1]
                wildcard_chains: List[MessageChain] = []
                if pattern.last is CommandPattern.ELast.REQUIRED:
                    if len(text_str) - 1 != scan_index or (
                        isinstance(tokens, set) and text_str[-1] not in tokens
                    ):
                        raise ValueError("Mismatch")
                    if isinstance(tokens, list):
                        for slot in tokens:
                            slot_data[slot] = MessageChain.fromMappingString(text_str[-1], elem_m)
                elif pattern.last is CommandPattern.ELast.OPTIONAL:
                    if len(text_str) - 1 == scan_index:  # matched
                        for slot in tokens:
                            slot_data[slot] = MessageChain.fromMappingString(text_str[-1], elem_m)
                    elif len(text_str) == scan_index:  # not matched
                        pass
                    else:  # length overflow
                        raise ValueError("Mismatch")
                elif pattern.last is CommandPattern.ELast.WILDCARD:
                    wildcard_chains = [
                        MessageChain.fromMappingString(text, elem_m) for text in text_str[scan_index:]
                    ]
                handler.set_data(slot_data, arg_data, wildcard_chains)

                await self.broadcast.Executor(handler)
