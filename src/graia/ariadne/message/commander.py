"""Commander: 便捷的指令触发体系"""
import inspect
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Sequence,
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
from .chain import MessageChain
from .element import Element
from .parser.twilight import ArgumentMatch, ParamMatch, Sparkle, Twilight
from .parser.util import CommandToken, tokenize_command

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
        value = value.asDisplay()
    if not value:
        value = field.default
    return value


class Slot:
    """Slot"""

    @overload
    def __init__(self, slot: Union[str, int], type: Type = MessageChain, default=...) -> None:
        ...

    def __init__(self, slot: Union[str, int], type: Type = ..., default=...) -> None:
        self.slot = slot
        self.type = type
        self.default = default
        self.param_name: str = ""


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
        self.args: List[str] = []
        self.tags: List[str] = []
        self.param_name: str = ""
        self.default_factory = (lambda: default) if default is not ... else default_factory
        if (default is ...) == (default_factory is ...):
            raise ValueError("default and default_factory is both empty / not empty!")

        for index, (t_type, token_list) in enumerate(tokenize_command(pattern)):
            if t_type is CommandToken.TEXT:
                t_type = CommandToken.CHOICE  # it's a argument pattern at header

            if t_type is CommandToken.CHOICE:
                if index == 0:
                    self.args = token_list
                else:
                    raise ValueError(
                        """"Argument pattern can only be placed at head. """
                        """Use "{" and "}" for placeholders."""
                    )
            if t_type is CommandToken.PARAM:
                if len(token_list) != 1:
                    raise ValueError("Arg doesn't support aliasing!")
                self.tags.append(str(token_list[0]))

        if self.tags:
            self.arg_match = ArgumentMatch(*self.args, nargs=len(self.tags))
        else:
            if default_factory is not ... or not isinstance(default, bool):
                raise ValueError(
                    "Boolean type Arg doesn't support default_factory / default value other than bool value!"
                )
            self.arg_match = ArgumentMatch(
                *self.args, action={False: "store_true", True: "store_false"}[default]
            )

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

        if issubclass(type, BaseModel) and not issubclass(type, AriadneBaseModel):
            self.model = type

        if self.model is ...:
            raise ValueError("You didn't supply a suitable type!")


class CommanderReference(NamedTuple):
    """CommandReference NamedTuple"""

    twilight: Twilight[Sparkle]
    slot_map: Dict[Union[str, int], Union[Slot, Arg]]
    func: Callable
    dispatchers: Sequence[BaseDispatcher]
    decorators: Sequence[Decorator]


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
        self.refs: List[CommanderReference] = []

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

        def wrapper(func: T_Callable) -> T_Callable:
            """append func to self.refs"""

            # ANCHOR: scan function signature

            sig = {}

            for name, parameter in inspect.signature(func).parameters.items():
                sig[name] = (parameter.annotation, parameter.default)

            arg_match: List[ArgumentMatch] = []
            slot_map: Dict[Union[Sequence[str], int, str], Union[Slot, Arg]] = {}
            optional_slot: List[Union[str, int]] = []
            for param_name, arg in setting.items():  # ANCHOR: scan setting
                # pylint: disable=cell-var-from-loop
                arg.param_name = param_name
                if isinstance(arg, Arg):
                    if arg.default_factory is ...:
                        if arg.param_name in sig and sig[arg.param_name][1] is not inspect.Signature.empty:
                            arg.default_factory = lambda: sig[arg.param_name][1]
                        else:
                            raise ValueError(f"Didn't find default for parameter {arg.param_name}")
                    arg_match.append(arg.arg_match)
                    slot_map[arg.arg_match.pattern] = arg
                elif isinstance(arg, Slot):
                    slot_map[arg.slot] = arg
                    if arg.default is not ...:
                        optional_slot.append(arg.slot)
                    if arg.type is ... and sig[arg.param_name][0] is not inspect.Signature.empty:
                        if arg.param_name in sig:
                            arg.type = sig[arg.param_name][0]
                        else:
                            arg.type = MessageChain

            sparkle_root: Sparkle = Sparkle.from_command(command, arg_match, optional_slot)
            if any(param.optional for param in sparkle_root[ParamMatch].__getitem__(slice(None, -1))):
                raise ValueError("You can only set last parameter as optional.")

            self.refs.append(
                CommanderReference(Twilight(sparkle_root), slot_map, func, dispatchers, decorators)
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
        handled = False

        for cmd_ref in self.refs:
            slot_map = cmd_ref.slot_map
            try:
                sparkle = cmd_ref.twilight.generate(chain)
                param_result: Dict[str, Any] = {}

                for param_match in sparkle[ParamMatch]:
                    for tag in param_match.tags:
                        if tag not in slot_map:
                            continue

                        slot: Slot = slot_map[tag]

                        slot_model = create_model(
                            "SlotModel",
                            __validators__={
                                "validator": validator("*", pre=True, allow_reuse=True)(chain_validator)
                            },
                            val=(slot.type, slot.default),
                        )
                        value = slot_model(val=param_match.result).__dict__["val"]

                        param_result[slot.param_name] = value

                for arg_match in sparkle[ArgumentMatch]:
                    arg: Arg = slot_map[arg_match.pattern]
                    value = arg.default_factory() if not arg_match.matched else arg_match.result
                    if not arg.tags:  # boolean
                        param_result[arg.param_name] = arg.model(val=value).__dict__["val"]
                    else:
                        if not isinstance(value, list):
                            value = [value]
                        param_result[arg.param_name] = arg.model(**dict(zip(arg.tags, value)))
                        if not (
                            isinstance(arg.type, Type)
                            and issubclass(arg.type, BaseModel)
                            and not issubclass(arg.type, AriadneBaseModel)
                        ):
                            param_result[arg.param_name] = param_result[arg.param_name].__dict__[arg.tags[0]]
            except ValueError:
                continue
            else:
                handled = True

                self.broadcast.loop.create_task(
                    self.broadcast.Executor(
                        ExecTarget(
                            cmd_ref.func,
                            inline_dispatchers=[
                                CommanderDispatcher(param_result),
                                ContextDispatcher(),
                                *cmd_ref.dispatchers,
                            ],
                            decorators=list(cmd_ref.decorators),
                        )
                    )
                )

        if not handled:
            raise ValueError(f"{chain!r} is not handled!")
