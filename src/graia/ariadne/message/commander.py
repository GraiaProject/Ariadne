"""Commander: 便捷的指令触发体系"""
import dataclasses
import inspect
import itertools
from contextlib import suppress
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Type,
    TypeVar,
    Union,
    overload,
)

from graia.broadcast import Broadcast
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.exectarget import ExecTarget
from pydantic import BaseModel, create_model, validator
from pydantic.fields import ModelField

from ..dispatcher import ContextDispatcher
from ..model import AriadneBaseModel
from ..typing import T
from ..util import ConstantDispatcher, resolve_dispatchers_mixin
from .chain import MessageChain
from .element import Element
from .parser.util import CommandToken, split, tokenize_command

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
    if field.type_ is MessageChain:
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


def const_call(val: T) -> Callable[[], T]:
    """生成一个返回常量的 Callable

    Args:
        val (T): 常量

    Returns:
        Callable[[], T]: 返回的函数
    """
    return lambda: val


class Slot:
    """Slot"""

    @overload
    def __init__(self, slot: Union[str, int], type: Type = MessageChain, default=...) -> None:
        ...

    def __init__(
        self,
        slot: Union[str, int],
        type: Type = ...,
        default: Any = ...,
        default_factory: Callable[[], Any] = ...,
    ) -> None:
        self.slot = slot
        self.type = type
        self.default_factory = ...
        self.param_name: str = ""
        self.model: Optional[BaseModel] = None

        if default is not ... and default_factory is not ...:
            raise ValueError("default and default_factory is both set!")

        if default is not ...:
            self.default_factory = const_call(default)

        if default_factory is not ...:
            self.default_factory = default_factory


class Arg:
    """Argument"""

    def __init__(
        self,
        pattern: str,
        type: Type[Union[BaseModel, Any]] = ...,
        *,
        default: Any = ...,
        default_factory: Callable[[], Any] = ...,
    ) -> None:

        if default is not ... and default_factory is not ...:
            raise ValueError("default and default_factory is both set!")

        self.pattern: str = pattern
        self.match_patterns: List[str] = []
        self.tags: List[str] = []
        self.default_factory = const_call(default) if default is not ... else default_factory
        self.param_name: Optional[str] = None

        tokens = tokenize_command(pattern)

        if tokens[0][0] is CommandToken.PARAM:
            raise ValueError("Required argument pattern!")

        self.match_patterns = list(map(str, tokens[0][1]))

        for t_type, token_list in tokens[1:]:
            if t_type in {CommandToken.TEXT, CommandToken.CHOICE}:
                raise ValueError(
                    """"Argument pattern can only be placed at head. """
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
        self.model: Type[BaseModel] = ...

        if self.nargs == 0:
            self.type = type if type is not ... else bool

        elif self.nargs == 1:
            self.type = type if type is not ... else MessageChain

        if issubclass(self.type, BaseModel) and not issubclass(
            type, AriadneBaseModel
        ):  # filter MessageChain, Element, etc.
            self.model = self.type


@dataclasses.dataclass
class CommandPattern:
    """命令样式"""

    token_list: "List[Set[str] | List[int | str]]"
    slot_map: Dict[Union[str, int], Slot]
    arg_map: Dict[str, Arg]
    last_optional: bool = False


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
            value = slot_data.get(ind, None) or slot.default_factory()
            param_result[slot.param_name] = slot.model(val=value).__dict__["val"]

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

        setting = setting or {}

        token_list: "List[Set[str] | List[int | str]]" = []  # set: const, list: param

        slot_names: Set[Union[int, str]] = set()

        for t_type, tokens in tokenize_command(command):
            if t_type in {CommandToken.TEXT, CommandToken.CHOICE}:
                token_list.append(set(map(str, tokens)))
            else:
                token_list.append(tokens)
                for param_name in tokens:
                    if param_name in slot_names:
                        raise ValueError("Duplicated parameter slot!")
                    slot_names.add(param_name)

        def wrapper(func: T_Callable) -> T_Callable:
            """append func to self.refs"""

            # ANCHOR: scan function signature

            sig = {}

            for name, parameter in inspect.signature(func).parameters.items():
                sig[name] = (parameter.annotation, parameter.default)

                if name in slot_names and name not in setting:
                    setting[name] = Slot(name, parameter.annotation)

                    if parameter.default is not inspect.Signature.empty and not isinstance(
                        parameter.default, Decorator
                    ):
                        setting[name].default_factory = const_call(parameter.default)

            slot_map: Dict[Union[int, str], Slot] = {}
            arg_map: Dict[str, Arg] = {}
            last_optional = False
            for param_name, arg in setting.items():  # ANCHOR: scan setting
                arg.param_name = param_name
                if isinstance(arg, Arg):
                    if arg.default_factory is ...:
                        if (
                            arg.param_name in sig
                            and sig[arg.param_name][1] is not inspect.Signature.empty
                            and not isinstance(sig[arg.param_name][1], Decorator)
                        ):
                            arg.default_factory = const_call(sig[arg.param_name][1])
                        else:
                            raise ValueError(f"Didn't find default factory for parameter {arg.param_name}")
                    for param in arg.match_patterns:
                        if param in arg_map or param in slot_names:
                            raise ValueError("Duplicated parameter pattern!")
                        arg_map[param] = arg

                    if arg.model is not ...:
                        continue

                    if len(arg.tags) == 0:  # Set default
                        arg.model = create_model(
                            "ArgModel",
                            __validators__={
                                f"validator_{i}": validator("*", pre=True, allow_reuse=True)(v)
                                for i, v in zip(itertools.count(), self.validators)
                            },
                            val=(arg.type, ...),
                        )
                    elif len(arg.tags) == 1:
                        arg.model = create_model(
                            "ArgModel",
                            __validators__={
                                f"validator_{i}": validator("*", pre=True, allow_reuse=True)(v)
                                for i, v in zip(itertools.count(), self.validators)
                            },
                            **{arg.tags[0]: (arg.type, ...)},
                        )

                    if arg.model is ...:
                        raise ValueError(f"You didn't supply a suitable model for {arg}!")

                elif isinstance(arg, Slot):
                    slot_map[arg.slot] = arg
                    if arg.default_factory is not ...:
                        if not isinstance(token_list[-1], list) or arg.slot not in token_list[-1]:
                            raise ValueError("Optional slot can only be set on last parameter.")
                        last_optional = True
                    else:
                        if (
                            arg.param_name in sig
                            and sig[arg.param_name][1] is not inspect.Signature.empty
                            and not isinstance(sig[arg.param_name][1], Decorator)
                        ):
                            arg.default_factory = const_call(sig[arg.param_name][1])
                    if arg.type is ... and sig[arg.param_name][0] is not inspect.Signature.empty:
                        if arg.param_name in sig:
                            arg.type = sig[arg.param_name][0]
                        else:
                            arg.type = MessageChain

                    arg.model = create_model(
                        "SlotModel",
                        __validators__={
                            f"validator_{i}": validator("*", pre=True, allow_reuse=True)(v)
                            for i, v in zip(itertools.count(), self.validators)
                        },
                        val=(arg.type, ...),  # default is handled at exec
                    )

                else:
                    raise TypeError("Only Arg and Slot instances are allowed!")
            self.command_handlers.append(
                CommandHandler(
                    CommandPattern(token_list, slot_map, arg_map, last_optional),
                    func,
                    dispatchers,
                    decorators,
                )
            )

            return func

        return wrapper

    def execute(self, chain: MessageChain):
        """触发 Commander.

        Args:
            chain (MessageChain): 触发的消息链

        Raises:
            ValueError: 消息链没有被任何一个命令处理器函数接受
        """

        mapping_str, elem_m = chain.asMappingString()
        chain_args = split(mapping_str)

        for handler in reversed(self.command_handlers):  # starting from latest added
            pattern = handler.pattern
            chain_index = 0
            token_index = 0
            arg_data: Dict[str, List[MessageChain]] = {}
            slot_data: Dict[Union[str, int], MessageChain] = {}
            with suppress(
                IndexError,
            ):
                while chain_index < len(chain_args):
                    arg = chain_args[chain_index]
                    chain_index += 1
                    if arg in pattern.arg_map:  # Arg handle
                        if arg in arg_data:
                            raise ValueError("Duplicated argument.")
                        arg_data[arg] = []
                        for _ in range(pattern.arg_map[arg].nargs):
                            arg_data[arg].append(
                                MessageChain.fromMappingString(chain_args[chain_index], elem_m)
                            )
                            chain_index += 1

                    else:  # Constant and Slot handle
                        tokens = pattern.token_list[token_index]
                        token_index += 1
                        if isinstance(tokens, set) and arg not in tokens:
                            raise ValueError("Mismatched constant.")
                        if isinstance(tokens, list):
                            for slot in tokens:
                                slot_data[slot] = MessageChain.fromMappingString(arg, elem_m)

                if token_index < len(pattern.token_list) - int(pattern.last_optional):
                    continue

                handler.set_data(slot_data, arg_data)

                self.broadcast.loop.create_task(self.broadcast.Executor(handler))
