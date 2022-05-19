import asyncio
import inspect
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    MutableMapping,
    Optional,
    Type,
    Union,
)
from weakref import WeakValueDictionary

from graia.amnesia.launch.manager import LaunchManager
from graia.broadcast import Broadcast

from .connection import ConnectionMixin
from .connection.config import U_Config
from .model import LogConfig
from .service import ElizabethService
from .typing import T


class Ariadne:
    service: ClassVar[ElizabethService] = ElizabethService()
    launch_manager: ClassVar[LaunchManager] = LaunchManager()
    instances: ClassVar[MutableMapping[int, "Ariadne"]] = WeakValueDictionary()
    default_account: ClassVar[Optional[int]] = None
    held_objects: ClassVar[Dict[type, Any]] = {
        Broadcast: service.broadcast,
        asyncio.AbstractEventLoop: service.loop,
    }

    def __init__(
        self,
        connection: Union[Iterable[U_Config], int] = (),
        log_config: Optional[LogConfig] = None,
    ) -> None:
        if isinstance(connection, Iterable):
            account = Ariadne.service.add_configs(connection)[1]
        else:
            account = connection
        self.account: int = account
        assert account in Ariadne.service.connections, f"{account} is not configured"
        self.connection: ConnectionMixin = Ariadne.service.connections[account]
        self.log_config: LogConfig = log_config or LogConfig()
        self.connection.event_callbacks.append(self.log_config.event_hook(self))
        if account not in Ariadne.instances:
            Ariadne.instances[account] = self

    @classmethod
    def _patch_launch_manager(cls) -> None:
        if "http.universal_client" not in cls.launch_manager.launch_components:
            from graia.amnesia.builtins.aiohttp import AiohttpService

            cls.launch_manager.add_service(AiohttpService())

        if (
            "http.universal_server" in cls.service.launch_component.required
            and "http.universal_server" not in cls.launch_manager.launch_components
        ):
            from graia.amnesia.builtins.aiohttp import AiohttpServerService

            cls.launch_manager.add_service(AiohttpServerService())

        if "elizabeth.service" not in cls.launch_manager.launch_components:
            cls.launch_manager.add_service(cls.service)

    @classmethod
    async def launch(cls) -> None:
        assert asyncio.get_running_loop() is cls.service.loop, "ElizabethService attached to different loop"
        cls._patch_launch_manager()
        await cls.launch_manager.launch()

    @classmethod
    def launch_blocking(cls):
        cls._patch_launch_manager()
        cls.launch_manager.launch_blocking(loop=cls.service.loop)

    @classmethod
    def create(cls, typ: Type["T"], reuse: bool = True) -> "T":
        """利用 Ariadne 已有的信息协助创建实例.

        Args:
            cls (Type[T]): 需要创建的类.
            reuse (bool, optional): 是否允许复用, 默认为 True.

        Returns:
            T: 创建的类.
        """
        if typ in cls.held_objects:
            return cls.held_objects[typ]
        call_args: list = []
        call_kwargs: Dict[str, Any] = {}

        for name, param in inspect.signature(typ).parameters.items():
            if param.annotation in cls.held_objects and param.kind not in (
                param.VAR_KEYWORD,
                param.VAR_POSITIONAL,
            ):
                param_obj = cls.held_objects.get(param.annotation, param.default)
                if param_obj is param.empty:
                    param_obj = cls.create(param.annotation, reuse=True)
                if param.kind is param.POSITIONAL_ONLY:
                    call_args.append(param_obj)
                else:
                    call_kwargs[name] = param_obj

        obj: "T" = typ(*call_args, **call_kwargs)
        if reuse:
            cls.held_objects[typ] = obj
        return obj

    @classmethod
    def current(cls) -> "Ariadne":
        from .context import ariadne_ctx

        if ariadne_ctx.get(None):
            return ariadne_ctx.get()  # type: ignore
        if not cls.default_account:
            if len(cls.service.connections) != 1:
                raise ValueError("Ambiguous account reference: set Ariadne.default_account")
            cls.default_account = next(iter(cls.service.connections))
        return cls.instances.setdefault(cls.default_account, cls(cls.default_account))

    def __getattr__(self, snake_case_name: str) -> Callable:
        # snake_case to camelCase
        snake_segments = snake_case_name.split("_")
        camel_case_name = snake_segments[0] + "".join(s.capitalize() for s in snake_segments[1:])
        return self.__dict__[camel_case_name]
