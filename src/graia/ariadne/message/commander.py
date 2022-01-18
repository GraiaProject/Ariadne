"""Commander: 便捷的指令触发体系"""
import inspect
from contextlib import suppress
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
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
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from pydantic import BaseModel, create_model, validator
from pydantic.fields import ModelField

from ..dispatcher import ContextDispatcher
from ..model import AriadneBaseModel
from ..typing import T
from ..util import resolve_dispatchers_mixin
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
        self.pattern: str = pattern
        self.params: List[str] = []
        self.tags: List[str] = []
        self.default_factory = const_call(default) if default is not ... else default_factory
        self.param_name: Optional[str] = None
        if (default is ...) == (default_factory is ...):
            raise ValueError("default and default_factory is both empty / not empty!")

        tokens = tokenize_command(pattern)

        if tokens[0][0] is CommandToken.PARAM:
            raise ValueError("Required argument pattern!")

        self.params = list(map(str, tokens[0][1]))

        if any(not arg.startswith("-") for arg in self.params):
            raise ValueError("Argument pattern should begin with a '-'!")

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

        if len(self.tags) == 0:  # Set default
            type = type if type is not ... else bool
            self.model = create_model(
                "ArgModel",
                __validators__={"validator": validator("*", pre=True, allow_reuse=True)(chain_validator)},
                val=(type, ...),
            )
        elif len(self.tags) == 1:
            type = type if type is not ... else MessageChain
            self.model = create_model(
                "ArgModel",
                __validators__={"validator": validator("*", pre=True, allow_reuse=True)(chain_validator)},
                **{self.tags[0]: (type, ...)},
            )

        if issubclass(type, BaseModel) and not issubclass(
            type, AriadneBaseModel
        ):  # filter MessageChain, Element, etc.
            self.model = type

        if self.model is ...:
            raise ValueError("You didn't supply a suitable type!")


class CommandReference(NamedTuple):
    """CommandReference NamedTuple"""

    token_list: "List[Set[str] | List[int | str]]"
    slot_map: Dict[Union[str, int], Slot]
    arg_map: Dict[str, Arg]
    func: Callable
    dispatchers: Sequence[BaseDispatcher]
    decorators: Sequence[Decorator]
    last_optional: bool = False


class CommandProcessData(NamedTuple):
    """记录 Commander 处理时的临时数据"""

    ref: CommandReference
    param_data: Dict[Union[int, str], MessageChain]
    arg_data: Dict[str, List[MessageChain]]


class CommanderDispatcher(BaseDispatcher):
    "Command Dispatcher"

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data = data

    async def catch(self, interface: DispatcherInterface):
        if interface.name in self.data:
            return self.data[interface.name]


class Commander:
    """便捷的指令触发器"""

    def __init__(self, broadcast: Broadcast):
        self.broadcast = broadcast
        self.refs: List[CommandReference] = []

    def command(
        self,
        command: str,
        setting: Dict[str, Union[Slot, Arg]],
        dispatchers: Sequence[BaseDispatcher] = (),
        decorators: Sequence[Decorator] = (),
    ) -> Callable[[T_Callable], T_Callable]:
        """装饰一个命令处理函数

        Args:
            command (str): 要处理的命令
            setting (Dict[str, Union[Slot, Arg]]): 参数名 -> Slot | Arg 映射, 用于分配参数

        Raises:
            ValueError: 在将非最后一个参数设置为可选

        Returns:
            Callable[[T_Callable], T_Callable]: 装饰器
        """

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
                    for param in arg.params:
                        if param in arg_map or param in slot_names:
                            raise ValueError("Duplicated parameter pattern!")
                        arg_map[param] = arg

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
                            "validator": validator("*", pre=True, allow_reuse=True)(chain_validator)
                        },
                        val=(arg.type, ...),  # default is handled at exec
                    )

                else:
                    raise TypeError("Only Arg and Slot instances are allowed!")
            self.refs.append(
                CommandReference(token_list, slot_map, arg_map, func, dispatchers, decorators, last_optional)
            )

            return func

        return wrapper

    @staticmethod
    def resolve_result(pd: CommandProcessData) -> Dict[str, Any]:
        """解析 CommandProcessData 并返回可用于 CommanderDispatcher 的数据

        Args:
            pd (CommandProcessData): Command 解析数据

        Returns:
            Dict[str, Any]: 返回的分发参数字典
        """
        param_result: Dict[str, Any] = {}
        for arg in set(pd.ref.arg_map.values()):
            value = arg.default_factory()
            if arg.nargs:
                for param in arg.params:
                    if param in pd.arg_data:
                        value = dict(zip(arg.tags, pd.arg_data[param]))
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
                if any(param in pd.arg_data for param in arg.params):
                    value = not value
                param_result[arg.param_name] = arg.model(val=value).__dict__["val"]

        for ind, slot in pd.ref.slot_map.items():
            value = pd.param_data.get(ind, None) or slot.default_factory()
            param_result[slot.param_name] = slot.model(val=value).__dict__["val"]
        return param_result

    def execute(self, chain: MessageChain):
        """触发 Commander.

        Args:
            chain (MessageChain): 触发的消息链

        Raises:
            ValueError: 消息链没有被任何一个命令处理器函数接受
        """

        mapping_str, elem_m = chain.asMappingString()
        chain_args = split(mapping_str)
        process_data: List[CommandProcessData] = [CommandProcessData(ref, {}, {}) for ref in self.refs]

        for pd in reversed(process_data):  # starting from latest added
            chain_index = 0
            token_index = 0
            with suppress(IndexError):
                while chain_index < len(chain_args):
                    arg = chain_args[chain_index]
                    chain_index += 1
                    if arg in pd.ref.arg_map:  # Arg handle
                        if arg in pd.arg_data:
                            raise ValueError("Duplicated argument.")
                        pd.arg_data[arg] = []
                        for _ in range(pd.ref.arg_map[arg].nargs):
                            pd.arg_data[arg].append(
                                MessageChain.fromMappingString(chain_args[chain_index], elem_m)
                            )
                            chain_index += 1

                    else:  # Constant and Slot handle
                        tokens = pd.ref.token_list[token_index]
                        token_index += 1
                        if isinstance(tokens, set) and arg not in tokens:
                            raise ValueError("Mismatched constant.")
                        if isinstance(tokens, list):
                            for slot in tokens:
                                pd.param_data[slot] = MessageChain.fromMappingString(arg, elem_m)

                if token_index < len(pd.ref.token_list) - (1 if pd.ref.last_optional else 0):
                    continue

                param_result = self.resolve_result(pd)

                self.broadcast.loop.create_task(
                    self.broadcast.Executor(
                        ExecTarget(
                            pd.ref.func,
                            inline_dispatchers=resolve_dispatchers_mixin(
                                [
                                    CommanderDispatcher(param_result),
                                    ContextDispatcher(),
                                    *pd.ref.dispatchers,
                                ]
                            ),
                            decorators=list(pd.ref.decorators),
                        )
                    )
                )
