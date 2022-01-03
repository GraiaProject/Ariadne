"""Commander: 便捷的指令触发体系"""
from typing import Any, Callable, Dict, List, NamedTuple, Sequence, Type, TypeVar, Union

from graia.broadcast import Broadcast
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.exectarget import ExecTarget
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from pydantic import create_model, validator

from ..dispatcher import ContextDispatcher
from ..typing import T
from .chain import MessageChain
from .element import Element
from .parser.twilight import ArgumentMatch, ParamMatch, Sparkle, Twilight
from .parser.util import CommandToken, tokenize_command

T_Callable = TypeVar("T_Callable", bound=Callable)


class Slot:
    """Slot"""

    def __init__(self, slot: Union[str, int], type: Type[T] = MessageChain, default: T = ...) -> None:
        self.slot = slot
        self.type = type
        self.default = default
        self.param_name: str = ""


class Arg:
    """Argument"""

    def __init__(
        self, pattern: str, handler: Callable[[Union[Dict[Union[str, int], MessageChain], bool]], Any] = ...
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


class CommanderReference(NamedTuple):
    """CommandReference NamedTuple"""

    twilight: Twilight[Sparkle]
    slot_map: Dict[Union[str, int], Union[Slot, Arg]]
    func: Callable


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
        self, command: str, setting: Dict[str, Union[Slot, Arg]]
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
        arg_match: List[ArgumentMatch] = []
        slot_map: Dict[Union[Sequence[str], int, str], Union[Slot, Arg]] = {}
        optional_slot: List[Union[str, int]] = []
        for param_name, arg in setting.items():
            arg.param_name = param_name
            if isinstance(arg, Arg):
                arg_match.append(arg.arg_match)
                slot_map[arg.arg_match.pattern] = arg
            elif isinstance(arg, Slot):
                slot_map[arg.slot] = arg
                if arg.default is not ...:
                    optional_slot.append(arg.slot)

        sparkle_root: Sparkle = Sparkle.from_command(command, arg_match, optional_slot)
        if any(param.optional for param in sparkle_root[ParamMatch].__getitem__(slice(None, -1))):
            raise ValueError("You can only set last parameter as optional.")

        def wrapper(func: T_Callable) -> T_Callable:
            """append func to self.refs"""
            self.refs.append(CommanderReference(Twilight(sparkle_root), slot_map, func))
            return func

        return wrapper

    def execute(self, chain: MessageChain):
        """触发 Commander.

        Args:
            chain (MessageChain): 触发的消息链
        """
        for twilight, slot_map, func in self.refs:
            try:
                sparkle = twilight.generate(chain)
                param_result: Dict[str, Any] = {}

                for param_match in sparkle[ParamMatch]:
                    for tag in param_match.tags:
                        if tag in slot_map:
                            slot: Slot = slot_map[tag]
                            value = (
                                param_match.result.asMappingString()[0]
                                if param_match.matched
                                else slot.default
                            )

                            def msg_chain_validator(cls, v):
                                """validate message chain"""
                                # pylint: disable=cell-var-from-loop
                                if cls.__fields__["val"].type_ is MessageChain:
                                    return MessageChain.fromMappingString(
                                        v, param_match.result.asMappingString()[1]
                                    )
                                return v

                            def element_validator(cls, v):
                                """validate element"""
                                # pylint: disable=cell-var-from-loop
                                if issubclass(cls.__fields__["val"].type_, Element):
                                    chain = MessageChain.fromMappingString(
                                        v, param_match.result.asMappingString()[1]
                                    )
                                    assert len(chain) == 1
                                    assert isinstance(chain[0], cls.__fields__["val"].type_)
                                    return chain[0]
                                return v

                            value = create_model(
                                "CommanderValidator",
                                __validators__={
                                    "msg_chain_validator": validator("val", pre=True, allow_reuse=True)(
                                        msg_chain_validator
                                    ),
                                    "element_validator": validator("val", pre=True, allow_reuse=True)(
                                        element_validator
                                    ),
                                },
                                val=(slot.type, ...),
                            )(val=value).__getattribute__("val")

                            param_result[slot.param_name] = value

                for arg_match in sparkle[ArgumentMatch]:
                    arg: Arg = slot_map[arg_match.pattern]
                    if not arg_match.matched:
                        param_result[arg.param_name] = Ellipsis
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

            self.broadcast.loop.create_task(
                self.broadcast.Executor(
                    ExecTarget(func, [CommanderDispatcher(param_result), ContextDispatcher()])
                )
            )
