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
from pydantic import create_model, validator

from ..dispatcher import ContextDispatcher
from .chain import MessageChain
from .element import Element
from .parser.twilight import ArgumentMatch, ParamMatch, Sparkle, Twilight
from .parser.util import CommandToken, tokenize_command

T_Callable = TypeVar("T_Callable", bound=Callable)


class Slot:
    """Slot"""

    @overload
    def __init__(self, slot: Union[str, int], type: Type = MessageChain, default=...):
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
        handler: Callable[[Union[Dict[Union[str, int], MessageChain], bool]], Any] = ...,
        *,
        default: Any = ...,
        default_factory: Callable[[], Any] = ...,
    ) -> None:
        self.pattern: str = pattern
        self.handler: Callable[[Union[Dict[Union[str, int], MessageChain], bool]], Any] = handler

        self.args: List[str] = []
        self.tag_ids: List[int] = []
        self.tag_mapping: Dict[Union[int, str], int] = {}

        self.param_name: str = ""

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
                self.tag_ids.append(len(self.tag_ids))
                for token in token_list:
                    if token in self.tag_mapping:
                        raise ValueError(f"Duplicated tag reference: {token}")
                    self.tag_mapping[token] = self.tag_ids[-1]

        if self.tag_ids:
            self.arg_match = ArgumentMatch(*self.args, nargs=len(self.tag_ids))
        else:
            self.arg_match = ArgumentMatch(*self.args, action="store_true")

        if default is not ... and default_factory is not ...:
            raise ValueError("You supplied default and default_factory at the same time!")

        self.default_factory = (lambda: default) if default is not ... else default_factory


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

                        value, mapping = (
                            param_match.result.asMappingString()
                            if param_match.matched
                            else (slot.default, {})
                        )

                        def _validator(cls, v: str):
                            """validate message chain"""
                            # pylint: disable=cell-var-from-loop
                            if cls.__fields__["val"].type_ is MessageChain:
                                return MessageChain.fromMappingString(v, mapping)
                            if issubclass(cls.__fields__["val"].type_, Element):
                                chain = MessageChain.fromMappingString(v, mapping)
                                assert len(chain) == 1
                                assert isinstance(chain[0], cls.__fields__["val"].type_)
                                return chain[0]
                            return v

                        value = create_model(
                            "CommanderValidator",
                            __validators__={
                                "_validator": validator("val", pre=True, allow_reuse=True)(_validator),
                            },
                            val=(slot.type, ...),
                        )(val=value).__getattribute__("val")

                        param_result[slot.param_name] = value

                for arg_match in sparkle[ArgumentMatch]:
                    arg: Arg = slot_map[arg_match.pattern]
                    if not arg_match.matched:
                        param_result[arg.param_name] = arg.default_factory()
                        continue
                    if arg.handler is ...:
                        param_result[arg.param_name] = arg_match.result
                        continue
                    if arg.tag_mapping:
                        param_result[arg.param_name] = arg.handler(
                            {tag: arg_match.result[ref] for tag, ref in arg.tag_mapping.items()}
                        )
                    else:
                        param_result[arg.param_name] = arg.handler(arg_match.result)

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
