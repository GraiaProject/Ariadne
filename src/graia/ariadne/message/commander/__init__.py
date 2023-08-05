"""Commander: 便捷的指令触发体系"""
import abc
import asyncio
import contextlib
import copy
import inspect
from contextvars import ContextVar
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Deque,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from typing_extensions import Self

from pydantic import BaseConfig, BaseModel
from pydantic.class_validators import Validator
from pydantic.fields import ModelField

from graia.broadcast import Broadcast, Listener
from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.exectarget import ExecTarget
from graia.broadcast.exceptions import PropagationCancelled
from graia.broadcast.typing import T_Dispatcher
from graia.broadcast.utilles import dispatcher_mixin_handler

from ...context import event_ctx
from ...dispatcher import ContextDispatcher
from ...event.message import MessageEvent
from ...model.util import AriadneBaseModel
from ...typing import DictStrAny, MaybeFlag, Sentinel, Wrapper
from ...util import constant, gen_subclass, resolve_dispatchers_mixin, type_repr
from ..chain import MessageChain
from ..element import Element, Plain
from .util import (
    AnnotatedParam,
    ChainContent,
    ChainContentList,
    ContextVarDispatcher,
    MatchEntry,
    MatchNode,
    Param,
    Text,
    convert_empty,
    extract_str,
    raw,
    split,
    tokenize,
)

T_Callable = TypeVar("T_Callable", bound=Callable)


def chain_validator(value: Any, field: ModelField) -> Any:
    """MessageChain 处理函数.

    应用作 pydantic 的 Model validator.
    取决于字段类型标注, 若与消息链, 消息元素无关则会直接把消息链用 as_display 转换为字符串.

    Args:
        value (Any): 验证值
        field (ModelField): 当前的 model 字段
    """
    if not isinstance(value, list):
        return field.get_default() if value is None else value
    if not value:
        return field.get_default()
    if field.outer_type_ is MessageChain:
        return MessageChain(value)
    if isinstance(field.outer_type_, type) and issubclass(field.outer_type_, Element):
        assert len(value) == 1
        v = value[0]
        if field.outer_type_ is Plain:
            assert v.__class__ is str
            return Plain(v)
        assert v.__class__ is field.outer_type_
        return v
    value = MessageChain(value)
    if field.outer_type_ in (bool, str, int):
        return str(value)
    return value


def wildcard_validator(value: ChainContentList, field: ModelField) -> Any:
    if not isinstance(value, list):
        return value
    if field.outer_type_ is raw:
        return MessageChain(" ").join([MessageChain(v) for v in value])
    altered_field = copy.copy(field)
    altered_field.outer_type_ = field.type_
    return [chain_validator(v, altered_field) for v in value] or field.get_default() or []


class ParamDesc(abc.ABC):
    field: ModelField
    dest: str

    @abc.abstractmethod
    def populate_field(self, validators: Iterable[Callable]) -> None:
        """生成 ParamDesc 上的 ModelField.

        Args:
            validators (Iterable[Callable]): 用作 validator 的 Callable 可迭代对象
        """
        ...

    def validate(self, v: Any) -> Any:
        res, err = self.field.validate(v, {self.field.name: v}, loc=self.dest)
        if err:
            raise ValueError(err)
        return res


class _CommanderModelConfig(BaseConfig):
    copy_on_model_validation: bool = False
    arbitrary_types_allowed: bool = True


def _make_field(
    name: str,
    type: Type,
    default_factory: MaybeFlag[Callable[[], Any]],
    validators: Iterable[Callable] = (),
) -> ModelField:
    new_factory = None if default_factory is Sentinel else default_factory
    return ModelField(
        name=name,
        type_=type,
        model_config=_CommanderModelConfig,
        class_validators={
            f"#commander_validator_{i}#": Validator(v, pre=True, always=True)
            for i, v in enumerate(validators)
        },
        default_factory=new_factory,
        required=new_factory is None,
    )


class Slot(ParamDesc):
    """Slot"""

    def __init__(
        self,
        target: Union[str, int],
        type: MaybeFlag[Type[Any]] = Sentinel,
        default: MaybeFlag[Any] = Sentinel,
        default_factory: MaybeFlag[Callable[[], Any]] = Sentinel,
    ) -> None:
        """构建 Slot.

        Args:
            target (Union[str, int]): Slot 的目标 token 名
            type (type, optional): Slot 的类型
            default (Any, optional): 默认值
            default_factory (Callable[[], Any], optional): 默认值工厂函数
        """
        self.target = str(target)
        self.type: Union[Literal[Sentinel], Type[Any]] = type
        self.is_optional: bool = False
        self.is_wildcard: bool = False
        if self.type == "raw":
            self.type = raw
        self.default_factory: MaybeFlag[Callable[[], Any]] = (
            constant(default) if default is not Sentinel else default_factory
        )

    def populate_field(self, validators: Iterable[Callable]) -> None:
        if self.type is Sentinel:
            self.type = MessageChain if self.default_factory is Sentinel else self.default_factory().__class__
        if self.is_wildcard and self.type is not raw and not TYPE_CHECKING:
            self.type = List[self.type]
        self.is_optional = self.is_wildcard or (self.default_factory is not Sentinel)
        self.field = _make_field(
            self.target,
            self.type,
            self.default_factory,
            validators,
        )

    def merge(self, other: Self) -> Self:
        if self.type is Sentinel and other.type is not Sentinel:
            self.type = other.type
        if self.default_factory is Sentinel and other.default_factory is not Sentinel:
            self.default_factory = other.default_factory
        return self

    def __repr__(self) -> str:
        seg: List[str] = [
            "..." if self.is_wildcard else "",
            self.target,
            ": ",
            type_repr(self.type),
            f" = {self.default_factory()}" if self.default_factory is not Sentinel else "",
            f" -> {self.dest}" if self.dest != self.target else "",
        ]
        return f"Slot({''.join(seg)})"


class Arg(ParamDesc):
    """Argument"""

    headers: FrozenSet[str]

    def __init__(
        self,
        pattern: str,
        type: MaybeFlag[Type[Any]] = Sentinel,
        default: MaybeFlag[Any] = Sentinel,
        default_factory: MaybeFlag[Callable[[], Any]] = Sentinel,
    ) -> None:
        """初始化 Arg.

        Args:
            pattern (str): Arg 的匹配模板, 与 `Commander.command` 使用相同语法.
            type (type, optional): Arg 的类型
            default (Any, optional): 默认值
            default_factory (Callable[[], Any], optional): 默认值工厂函数
        """
        self.type: MaybeFlag[Type[Any]] = Sentinel
        self.tags: List[str] = []
        iter_tokens = iter(tokenize(pattern))
        headers = next(iter_tokens)
        assert isinstance(headers, Text), "Required argument pattern!"
        self.headers = headers.choice
        for token in iter_tokens:
            assert isinstance(token, Param), "Argument pattern can only be presented at header!"
            assert len(token.names) == 1, "Arg param cannot have alias!"
            self.tags.append(next(iter(token.names)))
        nargs = len(self.tags)
        if nargs == 0:
            self.type = bool
            self.default_factory = constant(False)
        elif nargs == 1:
            self.type = MessageChain
        if default is not Sentinel:
            self.default_factory = constant(default)
        elif default_factory is not Sentinel:
            self.default_factory = default_factory
        if type is not Sentinel:
            self.type = type

    def populate_field(self, validators: Iterable[Callable]) -> None:
        assert self.dest
        assert self.type is not Sentinel, f"{self} don't have an appropriate type!"
        assert self.default_factory is not Sentinel, f"{self} doesn't have default value!"
        self.field = _make_field(self.dest, self.type, Sentinel, validators)

    def update(self, annotation: MaybeFlag[Any], default: MaybeFlag[Any]) -> None:
        if self.type is Sentinel and annotation is not Sentinel:
            self.type = annotation
        if self.default_factory is Sentinel and default is not Sentinel:
            self.default_factory = constant(default)

    def __repr__(self) -> str:
        return f"Arg([{'|'.join(self.headers)}]{''.join(f' {{{tag}}}' for tag in self.tags)})"


class CommandEntry(MatchEntry, ExecTarget):
    """命令信息的存储数据结构, 同时可作为 ExecTarget"""

    def __init__(self, priority: int) -> None:
        self.priority = priority
        self.slot_map: Dict[str, Slot] = {}  # Slot.target -> Slot
        self.arg_map: Dict[str, Arg] = {}
        self.targets: Set[str] = set()
        self.header_map: Dict[str, Arg] = {}
        self.extra: Optional[AnnotatedParam] = None
        self._arg_name_map: Optional[Dict[Arg, str]] = None
        self._slot_targets: Optional[Tuple[FrozenSet[str], ...]] = None
        self.optional: List[Slot] = []
        self.wildcard: Optional[Slot] = None

    @property
    def arg_name_map(self) -> Dict[Arg, str]:
        if not self._arg_name_map:
            self._arg_name_map = {v: k for k, v in self.arg_map.items()}
        return self._arg_name_map

    @property
    def slot_targets(self) -> Tuple[FrozenSet[str], ...]:
        if not self._slot_targets:
            self._slot_targets = tuple(
                frozenset(name for name in param.names if name in self.slot_map) for param in self.params
            )
        return self._slot_targets

    def update_from_func(self) -> None:
        """从 ExecTarget.callable 更新 entry 的信息"""
        for name, parameter in inspect.signature(self.callable).parameters.items():
            annotation = convert_empty(parameter.annotation)
            default = convert_empty(parameter.default)
            if name in self.targets:
                parsed_slot = Slot(name, annotation, default)
                parsed_slot.dest = name  # assuming that name is consistent
                self.slot_map.setdefault(name, parsed_slot).merge(parsed_slot)  # parsed slot < provided slot
            if name in self.arg_map:
                self.arg_map[name].update(annotation, default)
            if default is not Sentinel:
                last_token = self.tokens[-1]
                assert isinstance(last_token, Param), "Expected Param, not Text!"
                assert (
                    self.slot_map[name].target in last_token.names
                ), "Not setting wildcard / optional on the last slot!"

    def compile_arg(self, compile_result: Dict[str, Any], arg_data: Dict[str, ChainContentList]) -> None:
        for arg in self.arg_name_map:
            if TYPE_CHECKING:
                assert arg.type is not Sentinel
            value = arg.default_factory()
            if arg.dest in arg_data:  # provided in arg_data
                if (
                    len(arg.tags) > 1
                    or issubclass(arg.type, BaseModel)  # user provided a model, then we have to zip it
                    and not issubclass(arg.type, AriadneBaseModel)
                ):
                    value = dict(zip(arg.tags, arg_data[arg.dest]))
                elif len(arg.tags):
                    value = arg_data[arg.dest]
                else:  # probably a bool, flip it
                    value = not value
            compile_result[arg.dest] = arg.validate(value)

    def compile_extra(self, compile_result: Dict[str, Any], extra_list: ChainContentList) -> Any:
        for index, slot in enumerate(self.optional):
            compile_result[slot.dest] = slot.validate(extra_list[index])
        if self.wildcard:
            compile_result[self.wildcard.dest] = self.wildcard.validate(extra_list[len(self.optional) :])

    def compile_param(
        self,
        slot_data: Dict[str, ChainContent],  # Slot.target -> ChainContent
        arg_data: Dict[str, ChainContentList],  # Arg.dest -> List[ChainContent]
        extras: ChainContentList,
    ) -> Dict[str, Any]:
        compile_result: Dict[str, Any] = {
            slot.dest: slot.validate(slot_data[target]) for target, slot in self.slot_map.items()
        }
        self.compile_arg(compile_result, arg_data)
        self.compile_extra(compile_result, extras)
        return compile_result


class ParseData(NamedTuple):
    index: int
    node: MatchNode[CommandEntry]
    params: Tuple[ChainContent, ...]


commander_param_ctx = ContextVar("commander_param_ctx")

param_dispatcher = ContextVarDispatcher(commander_param_ctx)


class Commander:
    """便利的指令触发体系"""

    def __init__(self, broadcast: Broadcast, listen: bool = True):
        """
        Args:
            broadcast (Broadcast): 事件系统
            listen (bool): 是否监听消息事件
        """
        self.broadcast = broadcast
        self._slot_validators: List[Callable] = [chain_validator]
        self._wildcard_validators: List[Callable] = [wildcard_validator]
        self._arg_validators: List[Callable] = [chain_validator]
        self.match_root: MatchNode[CommandEntry] = MatchNode()
        self.entries: Set[CommandEntry] = set()

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

    def add_type_cast(self, *caster: Callable, type: Literal["slot", "wildcard", "arg"] = "slot") -> None:
        """添加类型验证器 (type caster / validator)

        Args:
            *caster (Callable): 验证器
            type (Literal["slot", "wildcard", "arg"], optional): \
                应用验证器的区域, 默认为不是 wildcard 的 Slot.
        """
        assert type in ("slot", "wildcard", "arg")
        validators: List[Callable] = getattr(self, f"_{type}_validators")
        validators.extend(caster)

    @staticmethod
    def parse_command(command: str, entry: CommandEntry, nbsp: DictStrAny) -> None:
        """从传入的命令补充 entry 的信息

        Args:
            command (str): 命令
            entry (CommandEntry): 命令的 entry
            nbsp (DictStrAny): eval 的命名空间
        """
        tokenize_result: List[Union[Text, Param, AnnotatedParam]] = tokenize(command)
        have_optional: bool = False
        for token in tokenize_result:
            if isinstance(token, Text):
                assert all(
                    pattern not in entry.header_map for pattern in token.choice
                ), f"{token} conflicts with an Arg object!"

            elif isinstance(token, AnnotatedParam):
                assert token.name not in entry.targets, "Duplicated parameter slot!"
                entry.targets.add(token.name)
                parsed_slot = Slot(
                    token.name,
                    eval(
                        token.annotation or "_sentinel",
                        {"raw": raw, "_sentinel": Sentinel, **nbsp},
                    ),
                    eval(token.default or "_sentinel", {"_sentinel": Sentinel, **nbsp}),
                )
                parsed_slot.dest = token.name  # assuming that param_name is consistent
                slot = entry.slot_map.setdefault(token.name, parsed_slot).merge(
                    parsed_slot
                )  # parsed slot < provided slot
                if token.wildcard:
                    assert token is tokenize_result[-1], "Not setting wildcard on the last slot!"
                    slot.is_wildcard = True
                    entry.wildcard = slot
                    continue
                elif slot.default_factory is not Sentinel:  # Definitely an optional
                    have_optional = True
                    continue
            elif isinstance(token, Param):
                for name in token.names:
                    assert name not in entry.targets, "Duplicated parameter slot!"
                    entry.targets.add(name)
            assert not have_optional, "Optional Slot is mixed with other type of components!"
        MatchEntry.__init__(entry, tokenize_result)

    def command(
        self,
        command: str,
        settings: Optional[Dict[str, Union[Slot, Arg]]] = None,
        dispatchers: Sequence[T_Dispatcher] = (),
        decorators: Sequence[Decorator] = (),
        priority: int = 16,
        *,
        nbsp: Optional[DictStrAny] = None,
    ) -> Wrapper:
        """装饰一个命令处理函数

        Args:
            command (str): 要处理的命令
            settings (Dict[str, Union[Slot, Arg]], optional): 参数设置.
            dispatchers (Sequence[T_Dispatcher], optional): 可选的额外 Dispatcher 序列.
            decorators (Sequence[Decorator], optional): 可选的额外 Decorator 序列.
            nbsp (DictStrAny, optional): 可选的字符串评估命名空间.
        Raises:
            ValueError: 命令格式错误

        Returns:
            Callable[[T_Callable], T_Callable]: 装饰器
        """

        entry = CommandEntry(priority)
        self.entries.add(entry)  # Add strong ref

        for name, val in (settings or {}).items():
            if isinstance(val, Slot):
                entry.slot_map[val.target] = val
            elif isinstance(val, Arg):
                for header in val.headers:
                    entry.header_map[header] = val
                entry.arg_map[name] = val
            else:
                raise TypeError(f"Unknown setting value: {name} - {val!r}")
            val.dest = name

        def wrapper(func: T_Callable) -> T_Callable:
            Commander.parse_command(command, entry, {**func.__globals__, **(nbsp or {})})
            ExecTarget.__init__(
                entry,
                func,
                [
                    ContextDispatcher(),
                    *resolve_dispatchers_mixin(dispatchers),
                ],
                list(decorators),
            )
            entry.update_from_func()

            # compute optional slots dynamically
            for token in entry.tokens:
                if isinstance(token, Param):
                    for token in token.names:
                        if (slot := entry.slot_map.get(token)) and slot.default_factory is not Sentinel:
                            entry.optional.append(slot)
                            break

            # populate fields
            for slot in entry.slot_map.values():
                slot.populate_field(self._wildcard_validators if slot.is_wildcard else self._slot_validators)
            for arg in entry.arg_map.values():
                arg.populate_field(self._arg_validators)
            for optional_key in [k for k, v in entry.slot_map.items() if v.is_optional]:
                entry.slot_map.pop(optional_key)
            for _ in entry.optional:
                entry.nodes.pop()
            if entry.wildcard:
                entry.nodes.pop()  # the last optional / wildcard token should not be on the MatchGraph
            self.match_root.push(entry)
            return func

        return wrapper

    def parse_rest(
        self,
        index: int,
        frags: ChainContentList,
        params: Tuple[ChainContent, ...],
        entry: CommandEntry,
    ) -> Optional[Tuple[CommandEntry, dict]]:
        # walks down optional, wildcard and Arg
        # extract slot data based on entry
        slot_data: Dict[str, ChainContent] = {
            name: chain for targets, chain in zip(entry.slot_targets, params) for name in targets
        }
        # slam all the rest data inside extra_list
        extras: ChainContentList = []
        arg_data: Dict[str, ChainContentList] = {}
        # index frags
        while index < len(frags):
            frag: ChainContent = frags[index]
            if (str_frag := extract_str(frag)) in entry.header_map:
                arg = entry.header_map[str_frag]
                index += 1
                if arg.dest:
                    if arg.dest in arg_data:  # if the arg is already assigned
                        return
                    arg_data[arg.dest] = frags[index : index + len(arg.tags)]
                index += len(arg.tags)
                if index > len(frags):  # failed
                    return None
                continue
            else:
                extras.append(frags[index])
                index += 1
        if not entry.wildcard and len(extras) > len(entry.optional):
            return None
        if len(extras) < len(entry.optional):
            extras.extend([] for _ in range(len(entry.optional) - len(extras)))
        return entry, entry.compile_param(slot_data, arg_data, extras)

    async def execute(self, chain: MessageChain):
        """触发 Commander.

        Args:
            chain (MessageChain): 触发的消息链
        """

        frags = split(chain)
        pending_exec: Dict[int, List[Tuple[CommandEntry, dict]]] = {}
        pending_next: Deque[ParseData] = Deque([ParseData(0, self.match_root, ())])

        dispatchers: List[T_Dispatcher] = [param_dispatcher]

        if event := event_ctx.get(None):
            dispatchers.extend(dispatcher_mixin_handler(event.Dispatcher))

        def push_pending(index: int, nxt: MatchNode[CommandEntry], params: Tuple[ChainContent, ...]):
            for entry in nxt.entries:
                with contextlib.suppress(ValueError):
                    if res := self.parse_rest(index, frags, params, entry):
                        pending_exec.setdefault(res[0].priority, []).append(res)
            pending_next.append(ParseData(index, nxt, params))

        while pending_next:
            params: Tuple[ChainContent, ...]
            index, node, params = pending_next.popleft()
            if index >= len(frags):
                continue
            frag = frags[index]
            index += 1
            if (str_frag := extract_str(frag)) in node.next:
                if TYPE_CHECKING:
                    assert isinstance(str_frag, str)
                nxt = node.next[str_frag]
                push_pending(index, nxt, params)
            if Sentinel in node.next:
                nxt = node.next[Sentinel]
                push_pending(index, nxt, params + (frag,))

        for _, execution in sorted(pending_exec.items()):
            tasks: List[asyncio.Task] = []
            for entry, param in execution:
                commander_param_ctx.set(param)
                tasks.append(asyncio.create_task(self.broadcast.Executor(entry, dispatchers)))
            done, _ = await asyncio.wait(tasks)
            for task in done:
                if task.exception() and isinstance(task.exception(), PropagationCancelled):
                    raise PropagationCancelled
