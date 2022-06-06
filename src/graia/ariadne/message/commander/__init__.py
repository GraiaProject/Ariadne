"""Commander: 便捷的指令触发体系"""
import abc
import enum
import inspect
from contextlib import suppress
from contextvars import ContextVar
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
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

from graia.broadcast import Broadcast, Listener
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.exectarget import ExecTarget
from graia.broadcast.exceptions import ExecutionStop, RequirementCrashed
from pydantic import BaseModel, create_model, validator
from pydantic.fields import ModelField
from typing_extensions import LiteralString

from ...context import event_ctx
from ...dispatcher import ContextDispatcher
from ...event.message import MessageEvent
from ...model import AriadneBaseModel
from ...util import (
    ConstantDispatcher,
    constant,
    gen_subclass,
    get_stack_namespace,
    resolve_dispatchers_mixin,
)
from ..chain import MessageChain
from ..element import Element
from ..parser.util import CommandToken, CommandTokenTuple, split, tokenize_command

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
        return str(value)
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
        if self.type == "raw":
            self.type = _raw
        self.default = default
        self.default_factory = default_factory
        self.param_name: str = ""
        self.model: Optional[Type[BaseModel]] = None

    def gen_model(self, validators: Iterable[Callable]) -> None:
        if self.model or self.type is _raw:
            return

        self.default_factory = constant(self.default) if self.default is not ... else self.default_factory

        if self.type is ...:
            self.type = MessageChain

        self.model = create_model(
            "SlotModel",
            __validators__={
                f"#validator_{i}#": validator("*", pre=True, allow_reuse=True)(v)
                for i, v in enumerate(validators)
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

        assert tokens[0][0] in {CommandToken.TEXT, CommandToken.CHOICE}, "Required argument pattern!"

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
        self.model: Optional[Type[BaseModel]] = None

    def gen_model(self, validators: Iterable[Callable]) -> None:
        if self.model:
            return

        if self.nargs == 0:
            self.type = self.type if self.type is not ... else bool
            if self.default is ... and self.default_factory is ...:
                self.default = False
        elif self.nargs == 1:
            self.type = self.type if self.type is not ... else MessageChain
        self.default_factory = constant(self.default) if self.default is not ... else self.default_factory

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
                    for i, v in enumerate(validators)
                },
                val=(self.type, ...),
            )
        elif self.nargs == 1:
            self.model = create_model(
                "ArgModel",
                __validators__={
                    f"#validator_{i}#": validator("*", pre=True, allow_reuse=True)(v)
                    for i, v in enumerate(validators)
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
    last_type: ELast
    wildcard: str = ""


_raw = object()  # wildcard annotation object


class MismatchError(ValueError):
    """指令失配"""


commander_data_ctx: ContextVar[Dict[str, Any]] = ContextVar("commander_data_ctx", default={})


class CommandHandler(ExecTarget):
    """Command 的 ExecTarget 对象, 承担了参数提取等任务"""

    def __init__(
        self,
        record: CommandPattern,
        callable: Callable,
        dispatchers: Sequence[BaseDispatcher] = (),
        decorators: Sequence[Decorator] = (),
    ):
        super().__init__(
            callable,
            [
                ConstantDispatcher(commander_data_ctx),
                ContextDispatcher(),
                *resolve_dispatchers_mixin(dispatchers),
            ],
            list(decorators),
        )
        self.pattern: CommandPattern = record

    def get_data(
        self,
        slot_data: Dict[Union[int, str], MessageChain],
        arg_data: Dict[str, List[MessageChain]],
        wildcard_list: List[MessageChain],
    ) -> Dict[str, Any]:
        """基于 CommandRecord 与解析数据设置 ConstantDispatcher 参数

        Args:
            slot_data (Dict[Union[int, str], MessageChain]): Slot 的解析结果
            arg_data (Dict[str, List[MessageChain]]): Arg 的解析结果

        Returns:
            Dict[str, Any]: 参数
        """
        param_result: Dict[str, Any] = {}
        for arg in set(self.pattern.arg_map.values()):
            value = arg.default_factory()
            if TYPE_CHECKING:
                assert arg.param_name
                assert arg.model
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
            if TYPE_CHECKING:
                assert slot.model
            if slot.param_name != self.pattern.wildcard:
                value = slot_data.get(ind, None) or slot.default_factory()
                param_result[slot.param_name] = slot.model(val=value).__dict__["val"]
            elif slot.type is _raw:
                param_result[slot.param_name] = MessageChain([" "]).join(wildcard_list)
            else:
                param_result[slot.param_name] = tuple(
                    slot.model(val=chain).__dict__["val"] for chain in wildcard_list
                )
        return param_result


class Commander:
    """便利的指令触发体系"""

    def __init__(self, broadcast: Broadcast, listen: bool = True):
        """
        Args:
            broadcast (Broadcast): 事件系统
            listen (bool): 是否监听指令
        """
        self.broadcast = broadcast
        self.command_handlers: List[CommandHandler] = []
        self.validators: List[Callable] = [chain_validator]

        if listen:
            self.broadcast.listeners.append(
                Listener(
                    self.execute,
                    self.broadcast.getDefaultNamespace(),
                    list(gen_subclass(MessageEvent)),
                )
            )

    def __del__(self):
        self.broadcast.listeners = [i for i in self.broadcast.listeners if i.callable != self.execute]

    def add_type_cast(self, *caster: Callable):
        """添加类型验证器 (type caster / validator)"""
        self.validators = [*reversed(caster), *self.validators]

    def command(
        self,
        command: LiteralString,
        setting: Optional[Dict[str, Union[Slot, Arg]]] = None,
        dispatchers: Sequence[BaseDispatcher] = (),
        decorators: Sequence[Decorator] = (),
    ) -> Callable[[T_Callable], T_Callable]:
        """装饰一个命令处理函数

        Args:
            command (str): 要处理的命令
            setting (Dict[str, Union[Slot, Arg]], optional): 参数设置.
            dispatchers (Sequence[BaseDispatcher], optional): 可选的额外 Dispatcher 序列.
            decorators (Sequence[Decorator], optional): 可选的额外 Decorator 序列.

        Raises:
            ValueError: 命令格式错误

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
                assert not any(
                    token in pattern_arg_map for token in tokens
                ), f"{tokens} conflicts with a Arg object!"

                token_list.append(set(cast(List[str], tokens)))

            elif t_type is CommandToken.ANNOTATED:
                wildcard, name, annotation, default = cast(List[str], tokens)
                if wildcard or default:
                    assert (
                        tokens is command_tokens[-1][1]
                    ), "Not setting wildcard / optional on the last slot!"
                if wildcard:
                    last = CommandPattern.ELast.WILDCARD
                if default:
                    last = CommandPattern.ELast.OPTIONAL
                assert name not in placeholder_set, "Duplicated parameter slot!"
                placeholder_set.add(name)
                parsed_slot = Slot(
                    name,
                    eval(annotation or "...", *get_stack_namespace(1, {"raw": _raw})),
                    eval(default or "...", *get_stack_namespace(1)),
                )
                parsed_slot.param_name = name  # assuming that param_name is consistent
                if name in slot_map:
                    slot_map[name] = parsed_slot | slot_map[name]  # parsed slot < provided slot
                if wildcard:
                    wildcard_slot_name = name
                token_list.append([name])
            elif t_type is CommandToken.PARAM:
                for param_name in tokens:
                    assert param_name not in placeholder_set, "Duplicated parameter slot!"
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
                    if name in slot_map:
                        slot_map[name] = parsed_slot | slot_map[name]  # parsed slot < provided slot
                    if default is not ...:
                        assert all(
                            [
                                slot_map[name].placeholder in command_tokens[-1][1],
                                command_tokens[-1][0]
                                in {
                                    CommandToken.ANNOTATED,
                                    CommandToken.PARAM,
                                },
                            ]
                        ), "Not setting wildcard / optional on the last slot!"

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

        mapping_str, elem_m = chain._to_mapping_str()

        for handler in reversed(self.command_handlers):  # starting from latest added
            pattern = handler.pattern
            text_index: int = 0
            token_index: int = 0
            arg_data: Dict[str, List[MessageChain]] = {}
            slot_data: Dict[Union[str, int], MessageChain] = {}
            text_list: List[str] = split(mapping_str)
            wildcard_list: List[MessageChain] = []
            with suppress(IndexError, MismatchError, ValueError, RequirementCrashed, ExecutionStop):
                while text_index < len(text_list):
                    text = text_list[text_index]
                    text_index += 1

                    if text in pattern.arg_map:  # Arg handle
                        if text in arg_data:
                            raise MismatchError("Duplicated argument")
                        nargs: int = pattern.arg_map[text].nargs
                        arg_data[text] = [
                            MessageChain._from_mapping_string(t, elem_m)
                            for t in text_list[text_index : text_index + nargs]
                        ]
                        text_index += nargs

                    else:  # Constant and Slot handle
                        tokens = pattern.token_list[token_index]
                        token_index += 1
                        if isinstance(tokens, set) and text not in tokens:
                            raise MismatchError
                        if isinstance(tokens, list):
                            if pattern.last_type is CommandPattern.ELast.WILDCARD and token_index == len(
                                pattern.token_list
                            ):
                                wildcard_list.append(MessageChain._from_mapping_string(text, elem_m))
                                token_index -= 1
                            for slot in tokens:
                                slot_data[slot] = MessageChain._from_mapping_string(text, elem_m)

                if text_index < len(pattern.token_list) - (
                    pattern.last_type is not CommandPattern.ELast.REQUIRED
                ):
                    continue

                dispatchers = []
                if event := event_ctx.get(None):
                    dispatchers = resolve_dispatchers_mixin([event.Dispatcher])
                token = commander_data_ctx.set(handler.get_data(slot_data, arg_data, wildcard_list))
                await self.broadcast.Executor(handler, dispatchers)
                commander_data_ctx.reset(token)
