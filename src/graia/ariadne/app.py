"""Ariadne 实例"""

import asyncio
import base64
import io
import os
import signal
import sys
import traceback
from contextlib import ExitStack, suppress
from datetime import datetime, timedelta
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    ClassVar,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Type,
    Union,
    cast,
    overload,
)

from launart import Launart
from loguru import logger

from graia.amnesia.builtins.memcache import Memcache, MemcacheService
from graia.amnesia.transport.common.storage import CacheStorage
from graia.broadcast import Broadcast
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from .connection import ConnectionInterface
from .connection._info import U_Info
from .connection.util import CallMethod, UploadMethod, build_event
from .context import enter_context, enter_message_send_context
from .event import MiraiEvent
from .event.message import (
    ActiveFriendMessage,
    ActiveGroupMessage,
    ActiveMessage,
    ActiveTempMessage,
    FriendMessage,
    GroupMessage,
    MessageEvent,
    TempMessage,
)
from .event.mirai import FriendEvent, GroupEvent
from .exception import AriadneConfigurationError, UnknownTarget
from .message import Source
from .message.chain import MessageChain, MessageContainer
from .model import (
    Announcement,
    FileInfo,
    Friend,
    Group,
    GroupConfig,
    LogConfig,
    Member,
    MemberInfo,
    Profile,
    Stranger,
)
from .model.relationship import Client
from .model.util import AriadneOptions
from .service import ElizabethService
from .typing import (
    SendMessageActionProtocol,
    SendMessageDict,
    SendMessageException,
    Sentinel,
    T,
    class_property,
)
from .util import (
    RichLogInstallOptions,
    ariadne_api,
    camel_to_snake,
    loguru_exc_callback,
    loguru_exc_callback_async,
)

if TYPE_CHECKING:
    from .message.element import Image, Voice


class Ariadne:
    """Ariadne, 一个优雅且协议完备的 Python QQ Bot 框架."""

    options: ClassVar[AriadneOptions] = {}
    service: ClassVar[ElizabethService]
    launch_manager: ClassVar[Launart]
    instances: ClassVar[Dict[int, "Ariadne"]] = {}

    account: int
    connection: ConnectionInterface
    default_send_action: SendMessageActionProtocol
    log_config: LogConfig

    @class_property
    def broadcast(cls) -> Broadcast:
        """获取 Ariadne 的事件系统.

        Returns:
            Broadcast: 事件系统
        """
        return cls.service.broadcast

    @class_property
    def default_account(cls) -> int:
        """获取默认账号.

        Returns:
            int: 默认账号
        """
        if "default_account" in Ariadne.options:
            return Ariadne.options["default_account"]
        raise ValueError("No default account configured")

    @classmethod
    def _ensure_config(cls):
        if not hasattr(cls, "service"):
            cls.service = ElizabethService()
        if not hasattr(cls, "launch_manager"):
            cls.launch_manager = Launart()
        if "install_log" not in cls.options:
            sys.excepthook = loguru_exc_callback
            traceback.print_exception = loguru_exc_callback
        cls.service.loop.set_exception_handler(loguru_exc_callback_async)
        cls.options["installed_log"] = True

    @classmethod
    def config(
        cls,
        *,
        launch_manager: Optional[Launart] = None,
        default_account: Optional[int] = None,
        install_log: Union[bool, RichLogInstallOptions] = False,
        inject_bypass_listener: bool = False,
    ) -> None:
        """配置 Ariadne 全局参数, 未提供的值会自动生成合理的默认值

        注：请在实例化 Ariadne 前配置完成

        Args:
            launch_manager (Optional[LaunchManager], optional): 启动管理器
            default_account (Optional[int], optional): 默认账号
            install_log (Union[bool, RichLogInstallOptions], optional): 是否安装 rich 日志, 默认为 False
            inject_bypass_listener (bool, optional): 是否注入透传 Broadcast, 默认为 False
        """

        if launch_manager:
            if getattr(cls, "launch_manager", launch_manager) is not launch_manager:
                raise AriadneConfigurationError("Inconsistent launch manager")
            cls.launch_manager = launch_manager

        if default_account:
            if "default_account" not in cls.options:
                cls.options["default_account"] = default_account
            elif cls.options["default_account"] != default_account:
                raise AriadneConfigurationError("Inconsistent default account")

        if install_log and "installed_log" not in cls.options:
            import richuru

            option = (
                install_log if isinstance(install_log, RichLogInstallOptions) else RichLogInstallOptions()
            )

            richuru.install(**option._asdict())
            traceback.print_exception = option.exc_hook
            cls.options["installed_log"] = True

        if inject_bypass_listener and "inject_bypass_listener" not in cls.options:
            import creart

            from .util import inject_bypass_listener as inject

            inject(creart.it(Broadcast))

    def __init__(
        self,
        connection: Iterable[U_Info] = (),
        log_config: Optional[LogConfig] = None,
    ) -> None:
        """针对单个账号初始化 Ariadne 实例.

        若需全局配置, 请使用 `Ariadne.config()`

        Args:
            connection (Iterable[U_Info]): 连接信息, 通过 `graia.ariadne.connection.config` 生成
            log_config (Optional[LogConfig], optional): 日志配置

        Returns:
            None: 无返回值
        """
        self._ensure_config()
        from .util.send import Strict

        self.default_send_action = Strict
        conns, account = Ariadne.service.add_infos(connection)
        for conn in conns:
            Ariadne.launch_manager.add_launchable(conn)
        if account in Ariadne.instances:
            raise AriadneConfigurationError("You can't configure an account twice!")
        Ariadne.instances[account] = self
        self.account: int = account
        if account not in Ariadne.service.connections:
            raise AriadneConfigurationError(f"{account} is not configured")
        self.connection: ConnectionInterface = Ariadne.service.get_interface(ConnectionInterface).bind(
            account
        )
        self.log_config: LogConfig = log_config or LogConfig()
        self.connection.add_callback(self.log_config.event_hook(self))
        self.connection.add_callback(self._event_hook)

    async def _event_hook(self, event: MiraiEvent):
        with ExitStack() as stack:
            stack.enter_context(enter_context(self, event))
            sys.audit("AriadnePostRemoteEvent", event)
            cache_set = self.launch_manager.get_interface(Memcache).set

            if isinstance(event, (MessageEvent, ActiveMessage)):
                await cache_set(f"account.{self.account}.message.{int(event)}", event, timedelta(seconds=120))
                if not event.message_chain:
                    event.message_chain.append("<! 不支持的消息类型 !>")

            if isinstance(event, FriendEvent):
                stack.enter_context(enter_message_send_context(UploadMethod.Friend))

                friend: Optional[Friend] = getattr(event, "sender", None) or getattr(event, "friend", None)
                if friend:
                    await cache_set(
                        f"account.{self.account}.friend.{int(friend)}", friend, timedelta(seconds=120)
                    )

            elif isinstance(event, GroupEvent):
                stack.enter_context(enter_message_send_context(UploadMethod.Group))
                group = cast(Optional[Group], getattr(event, "group", None))

                member = cast(
                    Optional[Member],
                    getattr(event, "sender", None)
                    or getattr(event, "member", None)
                    or getattr(event, "operator", None)
                    or getattr(event, "inviter", None),
                )
                if member:
                    if not group:
                        group = member.group
                    await cache_set(
                        f"account.{self.account}.group.{int(group)}.member.{int(member)}",
                        member,
                        timedelta(seconds=120),
                    )

                if group:
                    await cache_set(
                        f"account.{self.account}.group.{int(group)}", group, timedelta(seconds=120)
                    )

            self.service.broadcast.postEvent(event)

    @classmethod
    def _patch_launch_manager(cls) -> None:
        from graia.amnesia.builtins.aiohttp import AiohttpClientInterface
        from graia.amnesia.transport.common.server import AbstractRouter

        with suppress(ImportError):
            import creart

            from graia.scheduler import GraiaScheduler
            from graia.scheduler.service import SchedulerService

            if SchedulerService not in cls.launch_manager._service_bind:
                cls.launch_manager.add_service(SchedulerService(creart.it(GraiaScheduler)))

        if AiohttpClientInterface not in cls.launch_manager._service_bind:
            from graia.amnesia.builtins.aiohttp import AiohttpClientService

            cls.launch_manager.add_service(AiohttpClientService())

        if AbstractRouter in cls.service.required and AbstractRouter not in cls.launch_manager._service_bind:
            from graia.amnesia.builtins.aiohttp import AiohttpServerService

            cls.launch_manager.add_service(AiohttpServerService())

        if "elizabeth.service" not in cls.launch_manager.launchables:
            cls.launch_manager.add_service(cls.service)

        if "default_account" not in cls.options and len(cls.service.connections) == 1:
            cls.options["default_account"] = next(iter(cls.service.connections))

        if CacheStorage not in cls.launch_manager._service_bind:
            cls.launch_manager.add_service(MemcacheService())

    @classmethod
    def launch_blocking(cls, stop_signals: Iterable[signal.Signals] = (signal.SIGINT,)):
        """以阻塞方式启动 Ariadne

        Args:
            stop_signals (Iterable[signal.Signals], optional): 要监听的停止信号，默认为 `(signal.SIGINT,)`
        """
        if not cls.instances:
            raise ValueError("No account specified.")
        cls._patch_launch_manager()
        try:
            cls.launch_manager.launch_blocking(loop=cls.service.loop, stop_signal=stop_signals)
        except asyncio.CancelledError:
            logger.info("Launch manager exited.", style="red")

    @classmethod
    def stop(cls):
        """计划停止 Ariadne"""
        mgr = cls.launch_manager
        mgr.status.exiting = True
        if mgr.task_group is not None:
            mgr.task_group.stop = True
            task = mgr.task_group.blocking_task
            if task and not task.done():
                task.cancel()

    @classmethod
    def create(cls, typ: Type[T], reuse: bool = True) -> T:
        """利用 Ariadne 已有的信息协助创建实例.

        Args:
            cls (Type[T]): 需要创建的类.
            reuse (bool, optional): 是否允许复用, 默认为 True.

        Returns:
            T: 创建的类.
        """
        import creart

        return creart.it(typ, cache=reuse)

    @classmethod
    def current(cls, account: Optional[int] = None) -> "Ariadne":
        """获取 Ariadne 的当前实例.

        Returns:
            Ariadne: 当前实例.
        """
        if account:
            assert account in Ariadne.service.connections, f"{account} is not configured"
            return Ariadne.instances[account]
        from .context import ariadne_ctx

        if ariadne_ctx.get(None):
            return ariadne_ctx.get()
        if "default_account" not in cls.options:
            raise ValueError("Ambiguous account reference, set Ariadne.default_account")
        return Ariadne.instances[cls.options["default_account"]]

    @ariadne_api
    async def get_version(self, *, cache: bool = False) -> str:
        """获取后端 Mirai HTTP API 版本.

        Args:
            cache (bool, optional): 是否缓存结果, 默认为 False.

        Returns:
            str: 版本信息.
        """
        interface = self.launch_manager.get_interface(Memcache)
        if cache and (version := await interface.get(f"account.{self.account}.version")):
            return version
        version = (await self.connection.call("about", CallMethod.GET, {}, in_session=False))["version"]
        await interface.set(f"account.{self.account}.version", version, timedelta(seconds=120))
        return version

    @ariadne_api
    async def get_bot_list(self) -> List[int]:
        """获取所有当前登录账号. 需要 Mirai API HTTP 2.6.0+.

        Returns:
            List[int]: 机器人列表.
        """
        return await self.connection.call("botList", CallMethod.GET, {}, in_session=False)

    async def get_file_iterator(
        self,
        target: Union[Group, int],
        id: str = "",
        offset: int = 0,
        size: int = 1,
        with_download_info: bool = False,
    ) -> AsyncGenerator[FileInfo, None]:
        """
        以生成器形式列出指定文件夹下的所有文件.

        Args:
            target (Union[Group, int]): 要列出文件的根位置, \
            为群组或群号 (当前仅支持群组)
            id (str): 文件夹ID, 空串为根目录
            offset (int): 起始分页偏移
            size (int): 单次分页大小
            with_download_info (bool): 是否携带下载信息, 无必要不要携带

        Returns:
            AsyncGenerator[FileInfo, None]: 文件信息生成器.
        """
        target = int(target)
        current_offset = offset
        cache: List[FileInfo] = []
        while True:
            for file_info in cache:
                yield file_info
            cache = await self.get_file_list(target, id, current_offset, size, with_download_info)
            current_offset += len(cache)
            if not cache:
                return

    @ariadne_api
    async def get_file_list(
        self,
        target: Union[Group, int],
        id: str = "",
        offset: Optional[int] = 0,
        size: Optional[int] = 1,
        with_download_info: bool = False,
    ) -> List[FileInfo]:
        """
        列出指定文件夹下的所有文件.

        Args:
            target (Union[Group, int]): 要列出文件的根位置, \
            为群组或群号 (当前仅支持群组)
            id (str): 文件夹ID, 空串为根目录
            offset (int): 分页偏移
            size (int): 分页大小
            with_download_info (bool): 是否携带下载信息, 无必要不要携带

        Returns:
            List[FileInfo]: 返回的文件信息列表.
        """
        target = int(target)

        result = await self.connection.call(
            "file_list",
            CallMethod.GET,
            {
                "id": id,
                "target": target,
                "withDownloadInfo": str(with_download_info),  # yarl don't accept boolean
                "offset": offset,
                "size": size,
            },
        )
        return [FileInfo.parse_obj(i) for i in result]

    @ariadne_api
    async def get_file_info(
        self,
        target: Union[Friend, Group, int],
        id: str = "",
        with_download_info: bool = False,
    ) -> FileInfo:
        """
        获取指定文件的信息.

        Args:
            target (Union[Friend, Group, int]): 要列出文件的根位置, \
            为群组或好友或QQ号 (当前仅支持群组)
            id (str): 文件ID, 空串为根目录
            with_download_info (bool): 是否携带下载信息, 无必要不要携带

        Returns:
            FileInfo: 返回的文件信息.
        """
        if isinstance(target, Friend):
            raise NotImplementedError("Not implemented for friend")

        target = target.id if isinstance(target, Friend) else target
        target = target.id if isinstance(target, Group) else target

        result = await self.connection.call(
            "file_info",
            CallMethod.GET,
            {
                "id": id,
                "target": target,
                "withDownloadInfo": str(with_download_info),  # yarl don't accept boolean
            },
        )

        return FileInfo.parse_obj(result)

    @ariadne_api
    async def make_directory(
        self,
        target: Union[Friend, Group, int],
        name: str,
        id: str = "",
    ) -> FileInfo:
        """
        在指定位置创建新文件夹.

        Args:
            target (Union[Friend, Group, int]): 要列出文件的根位置, \
            为群组或好友或QQ号 (当前仅支持群组)
            name (str): 要创建的文件夹名称.
            id (str): 上级文件夹ID, 空串为根目录

        Returns:
            FileInfo: 新创建文件夹的信息.
        """
        if isinstance(target, Friend):
            raise NotImplementedError("Not implemented for friend")

        target = target.id if isinstance(target, Friend) else target
        target = target.id if isinstance(target, Group) else target

        result = await self.connection.call(
            "file_mkdir",
            CallMethod.POST,
            {
                "id": id,
                "directoryName": name,
                "target": target,
            },
        )

        return FileInfo.parse_obj(result)

    @ariadne_api
    async def delete_file(
        self,
        target: Union[Friend, Group, int],
        id: str = "",
    ) -> None:
        """
        删除指定文件.

        Args:
            target (Union[Friend, Group, int]): 要列出文件的根位置, \
            为群组或好友或QQ号 (当前仅支持群组)
            id (str): 文件ID

        Returns:
            None: 没有返回.
        """
        if isinstance(target, Friend):
            raise NotImplementedError("Not implemented for friend")

        target = target.id if isinstance(target, Friend) else target
        target = target.id if isinstance(target, Group) else target

        await self.connection.call(
            "file_delete",
            CallMethod.POST,
            {
                "id": id,
                "target": target,
            },
        )

    @ariadne_api
    async def move_file(
        self,
        target: Union[Friend, Group, int],
        id: str = "",
        dest_id: str = "",
    ) -> None:
        """
        移动指定文件.

        Args:
            target (Union[Friend, Group, int]): 要列出文件的根位置, \
            为群组或好友或QQ号 (当前仅支持群组)
            id (str): 源文件ID
            dest_id (str): 目标文件夹ID

        Returns:
            None: 没有返回.
        """
        if isinstance(target, Friend):
            raise NotImplementedError("Not implemented for friend")

        target = target.id if isinstance(target, Friend) else target
        target = target.id if isinstance(target, Group) else target

        await self.connection.call(
            "file_move",
            CallMethod.POST,
            {
                "id": id,
                "target": target,
                "moveTo": dest_id,
            },
        )

    @ariadne_api
    async def rename_file(
        self,
        target: Union[Friend, Group, int],
        id: str = "",
        dest_name: str = "",
    ) -> None:
        """
        重命名指定文件.

        Args:
            target (Union[Friend, Group, int]): 要列出文件的根位置, \
            为群组或好友或QQ号 (当前仅支持群组)
            id (str): 源文件ID
            dest_name (str): 目标文件新名称.

        Returns:
            None: 没有返回.
        """
        if isinstance(target, Friend):
            raise NotImplementedError("Not implemented for friend")

        target = target.id if isinstance(target, Friend) else target
        target = target.id if isinstance(target, Group) else target

        await self.connection.call(
            "file_rename",
            CallMethod.POST,
            {
                "id": id,
                "target": target,
                "renameTo": dest_name,
            },
        )

    @ariadne_api
    async def upload_file(
        self,
        data: Union[bytes, IO[bytes], os.PathLike],
        method: Union[str, UploadMethod, None] = None,
        target: Union[Friend, Group, int] = -1,
        path: str = "",
        name: str = "",
    ) -> "FileInfo":
        """
        上传文件到指定目标, 需要提供: 文件的原始数据(bytes), 文件的上传类型, \
        上传目标, (可选)上传目录ID.

        Args:
            data (Union[bytes, IO[bytes], os.PathLike]): 文件的原始数据
            method (str | UploadMethod, optional): 文件的上传类型
            target (Union[Friend, Group, int]): 文件上传目标, 即群组
            path (str): 目标路径, 默认为根路径.
            name (str): 文件名, 可选, 若 path 存在斜杠可从 path 推断.

        Returns:
            FileInfo: 文件信息
        """
        method = str(method or UploadMethod[target.__class__.__name__]).lower()

        if method != "group":
            raise NotImplementedError(f"Not implemented for {method}")

        target = target.id if isinstance(target, (Friend, Group)) else target

        if "/" in path and not name:
            path, name = path.rsplit("/", 1)

        if isinstance(data, os.PathLike):
            data = open(data, "rb")

        result = await self.connection.call(
            "file_upload",
            CallMethod.MULTIPART,
            {
                "type": method,
                "target": str(target),
                "path": path,
                "file": {"value": data, **({"filename": name} if name else {})},
            },
        )

        return FileInfo.parse_obj(result)

    @ariadne_api
    async def upload_image(
        self, data: Union[bytes, IO[bytes], os.PathLike], method: Union[None, str, UploadMethod] = None
    ) -> "Image":
        """上传一张图片到远端服务器, 需要提供: 图片的原始数据(bytes), 图片的上传类型.

        Args:
            data (Union[bytes, IO[bytes], os.PathLike]): 图片的原始数据
            method (str | UploadMethod, optional): 图片的上传类型, 可从上下文推断
        Returns:
            Image: 生成的图片消息元素
        """
        from .context import upload_method_ctx
        from .message.element import Image

        method = str(method or upload_method_ctx.get()).lower()

        if isinstance(data, os.PathLike):
            data = open(data, "rb")

        result = await self.connection.call(
            "uploadImage",
            CallMethod.MULTIPART,
            {
                "type": method,
                "img": data,
            },
        )

        return Image.parse_obj(result)

    @ariadne_api
    async def upload_voice(
        self, data: Union[bytes, IO[bytes], os.PathLike], method: Union[None, str, UploadMethod] = None
    ) -> "Voice":
        """上传语音到远端服务器, 需要提供: 语音的原始数据(bytes), 语音的上传类型.

        Args:
            data (Union[bytes, IO[bytes], os.PathLike]): 语音的原始数据
            method (str | UploadMethod, optional): 语音的上传类型, 可从上下文推断
        Returns:
            Voice: 生成的语音消息元素
        """
        from .context import upload_method_ctx
        from .message.element import Voice

        method = str(method or upload_method_ctx.get()).lower()

        if isinstance(data, os.PathLike):
            data = open(data, "rb")

        result = await self.connection.call(
            "uploadVoice",
            CallMethod.MULTIPART,
            {
                "type": method,
                "voice": data,
            },
        )

        return Voice.parse_obj(result)

    async def get_announcement_iterator(
        self,
        target: Union[Group, int],
        offset: int = 0,
        size: int = 10,
    ) -> AsyncGenerator[Announcement, None]:
        """
        获取群公告列表.

        Args:
            target (Union[Group, int]): 指定的群组.
            offset (Optional[int], optional): 起始偏移量. 默认为 0.
            size (Optional[int], optional): 列表大小. 默认为 10.

        Returns:
            AsyncGenerator[Announcement, None]: 列出群组下所有的公告.
        """
        target = int(target)
        current_offset = offset
        cache: List[Announcement] = []
        while True:
            for announcement in cache:
                yield announcement
            cache = await self.get_announcement_list(target, current_offset, size)
            current_offset += len(cache)
            if not cache:
                return

    @ariadne_api
    async def get_announcement_list(
        self,
        target: Union[Group, int],
        offset: Optional[int] = 0,
        size: Optional[int] = 10,
    ) -> List[Announcement]:
        """
        列出群组下所有的公告.

        Args:
            target (Union[Group, int]): 指定的群组.
            offset (Optional[int], optional): 起始偏移量. 默认为 0.
            size (Optional[int], optional): 列表大小. 默认为 10.

        Returns:
            List[Announcement]: 列出群组下所有的公告.
        """
        result = await self.connection.call(
            "anno_list",
            CallMethod.GET,
            {
                "target": int(target),
                "offset": offset,
                "size": size,
            },
        )

        return [Announcement.parse_obj(announcement) for announcement in result]

    @ariadne_api
    async def publish_announcement(
        self,
        target: Union[Group, int],
        content: str,
        *,
        send_to_new_member: bool = False,
        pinned: bool = False,
        show_edit_card: bool = False,
        show_popup: bool = False,
        require_confirmation: bool = False,
        image: Optional[Union[str, bytes, os.PathLike, io.IOBase]] = None,
    ) -> Announcement:
        """
        发布一个公告.

        Args:
            target (Union[Group, int]): 指定的群组.
            content (str): 公告内容.
            send_to_new_member (bool, optional): 是否公开. 默认为 False.
            pinned (bool, optional): 是否置顶. 默认为 False.
            show_edit_card (bool, optional): 是否自动删除. 默认为 False.
            show_popup (bool, optional): 是否在阅读后自动删除. 默认为 False.
            require_confirmation (bool, optional): 是否需要确认. 默认为 False.
            image (Union[str, bytes, os.PathLike, io.IOBase, Image], optional): 图片. 默认为 None. \
            为 str 时代表 url, 为 bytes / os.PathLike / io.IOBase 代表原始数据

        Raises:
            TypeError: 提供了错误的参数, 阅读有关文档得到问题原因

        Returns:
            None: 没有返回.
        """
        data: Dict[str, Any] = {
            "target": int(target),
            "content": content,
            "sendToNewMember": send_to_new_member,
            "pinned": pinned,
            "showEditCard": show_edit_card,
            "showPopup": show_popup,
            "requireConfirmation": require_confirmation,
        }

        if image:
            if isinstance(image, bytes):
                data["imageBase64"] = base64.b64encode(image).decode("ascii")
            elif isinstance(image, os.PathLike):
                data["imageBase64"] = base64.b64encode(open(image, "rb").read()).decode("ascii")
            elif isinstance(image, io.IOBase):
                data["imageBase64"] = base64.b64encode(image.read()).decode("ascii")
            elif isinstance(image, str):
                data["imageUrl"] = image

        result = await self.connection.call(
            "anno_publish",
            CallMethod.POST,
            data,
        )
        return Announcement.parse_obj(result)

    @ariadne_api
    async def delete_announcement(self, target: Union[Group, int], anno: Union[Announcement, int]) -> None:
        """
        删除一条公告.

        Args:
            target (Union[Group, int]): 指定的群组.
            anno (Union[Announcement, int]): 指定的公告.

        Raises:
            TypeError: 提供了错误的参数, 阅读有关文档得到问题原因
        """
        await self.connection.call(
            "anno_delete",
            CallMethod.POST,
            {
                "target": int(target),
                "anno": anno.fid if isinstance(anno, Announcement) else anno,
            },
        )

    @ariadne_api
    async def delete_friend(self, target: Union[Friend, int]) -> None:
        """
        删除指定好友.

        Args:
            target (Union[Friend, int]): 好友对象或QQ号.

        Returns:
            None: 没有返回.
        """
        friend_id = target.id if isinstance(target, Friend) else target

        await self.connection.call(
            "deleteFriend",
            CallMethod.POST,
            {
                "target": friend_id,
            },
        )

    @ariadne_api
    async def mute_member(self, group: Union[Group, int], member: Union[Member, int], time: int) -> None:
        """
        在指定群组禁言指定群成员; 需要具有相应权限(管理员/群主);
        `time` 不得大于 `30*24*60*60=2592000` 或小于 `0`, 否则会自动修正;
        当 `time` 小于等于 `0` 时, 不会触发禁言操作;
        禁言对象极有可能触发 `PermissionError`, 在这之前请对其进行判断!

        Args:
            group (Union[Group, int]): 指定的群组
            member (Union[Member, int]): 指定的群成员(只能是普通群员或者是管理员, 后者则要求群主权限)
            time (int): 禁言事件, 单位秒, 修正规则: `0 < time <= 2592000`

        Raises:
            PermissionError: 没有相应操作权限.

        Returns:
            None: 没有返回.
        """
        time = max(0, min(time, 2592000))  # Fix time parameter
        if not time:
            return
        await self.connection.call(
            "mute",
            CallMethod.POST,
            {
                "target": group.id if isinstance(group, Group) else group,
                "memberId": member.id if isinstance(member, Member) else member,
                "time": time,
            },
        )

    @ariadne_api
    async def unmute_member(self, group: Union[Group, int], member: Union[Member, int]) -> None:
        """
        在指定群组解除对指定群成员的禁言;
        需要具有相应权限(管理员/群主);
        对象极有可能触发 `PermissionError`, 在这之前请对其进行判断!

        Args:
            group (Union[Group, int]): 指定的群组
            member (Union[Member, int]): 指定的群成员(只能是普通群员或者是管理员, 后者则要求群主权限)

        Raises:
            PermissionError: 没有相应操作权限.

        Returns:
            None: 没有返回.
        """
        await self.connection.call(
            "unmute",
            CallMethod.POST,
            {
                "target": group.id if isinstance(group, Group) else group,
                "memberId": member.id if isinstance(member, Member) else member,
            },
        )

    @ariadne_api
    async def mute_all(self, group: Union[Group, int]) -> None:
        """在指定群组开启全体禁言, 需要当前会话账号在指定群主有相应权限(管理员或者群主权限)

        Args:
            group (Union[Group, int]): 指定的群组.

        Returns:
            None: 没有返回.
        """
        await self.connection.call(
            "muteAll",
            CallMethod.POST,
            {
                "target": group.id if isinstance(group, Group) else group,
            },
        )

    @ariadne_api
    async def unmute_all(self, group: Union[Group, int]) -> None:
        """在指定群组关闭全体禁言, 需要当前会话账号在指定群主有相应权限(管理员或者群主权限)

        Args:
            group (Union[Group, int]): 指定的群组.

        Returns:
            None: 没有返回.
        """
        await self.connection.call(
            "unmuteAll",
            CallMethod.POST,
            {
                "target": group.id if isinstance(group, Group) else group,
            },
        )

    @ariadne_api
    async def kick_member(
        self, group: Union[Group, int], member: Union[Member, int], message: str = "", block: bool = False
    ) -> None:
        """
        将目标群组成员从指定群组踢出; 需要具有相应权限(管理员/群主)

        Args:
            group (Union[Group, int]): 指定的群组
            member (Union[Member, int]): 指定的群成员(只能是普通群员或者是管理员, 后者则要求群主权限)
            message (str, optional): 对踢出对象要展示的消息
            block (bool, optional): 是否不再接受该成员加群申请

        Returns:
            None: 没有返回.
        """
        await self.connection.call(
            "kick",
            CallMethod.POST,
            {
                "target": group.id if isinstance(group, Group) else group,
                "memberId": member.id if isinstance(member, Member) else member,
                "msg": message,
                "block": block,
            },
        )

    @ariadne_api
    async def quit_group(self, group: Union[Group, int]) -> None:
        """
        主动从指定群组退出

        Args:
            group (Union[Group, int]): 需要退出的指定群组

        Returns:
            None: 没有返回.
        """
        await self.connection.call(
            "quit",
            CallMethod.POST,
            {
                "target": group.id if isinstance(group, Group) else group,
            },
        )

    @ariadne_api
    async def set_essence(
        self,
        message: Union[GroupMessage, ActiveGroupMessage, Source, int],
        target: Optional[Union[Group, int]] = None,
    ) -> None:
        """
        添加指定消息为群精华消息; 需要具有相应权限(管理员/群主).

        请自行判断消息来源是否为群组.

        Note:
            后端 Mirai HTTP API 版本 >= 2.6.0, 仅指定 message 且类型为 Source 或 int 时, \
                将尝试使用缓存获得消息事件或以当前事件来源作为 target.

        Args:
            message (Union[GroupMessage, ActiveGroupMessage, Source, int]): 指定的消息.
            target (Union[Group, int], optional): 指定的群组. message 类型为 Source 或 int 时必需.

        Returns:
            None: 没有返回.
        """
        if isinstance(message, GroupMessage):
            target = message.sender.group
        elif isinstance(message, ActiveGroupMessage):
            target = message.subject

        if tuple(map(int, (await self.get_version(cache=True)).split("."))) >= (2, 6, 0):
            if target is not None:
                pass
            elif (
                event := await self.launch_manager.get_interface(Memcache).get(
                    f"account.{self.account}.message.{int(message)}"
                )
            ) and isinstance(event, (GroupMessage, ActiveGroupMessage)):
                return await self.set_essence(event)
            elif (
                target := await DispatcherInterface.ctx.get().lookup_param("target", Optional[Group], None)
            ) is None:
                raise TypeError("set_essence() missing 1 required positional argument: 'target'")

            params = {
                "messageId": int(message),
                "target": int(target),
            }
        else:
            params = {
                "target": int(message),
            }

        await self.connection.call("setEssence", CallMethod.POST, params)

    @ariadne_api
    async def get_group_config(self, group: Union[Group, int]) -> GroupConfig:
        """
        获取指定群组的群设置

        Args:
            group (Union[Group, int]): 需要获取群设置的指定群组

        Returns:
            GroupConfig: 指定群组的群设置
        """
        result = await self.connection.call(
            "groupConfig",
            CallMethod.RESTGET,
            {
                "target": group.id if isinstance(group, Group) else group,
            },
        )

        return GroupConfig.parse_obj({camel_to_snake(k): v for k, v in result.items()})

    @ariadne_api
    async def modify_group_config(self, group: Union[Group, int], config: GroupConfig) -> None:
        """修改指定群组的群设置; 需要具有相应权限(管理员/群主).

        Args:
            group (Union[Group, int]): 需要修改群设置的指定群组
            config (GroupConfig): 经过修改后的群设置

        Returns:
            None: 没有返回.
        """
        await self.connection.call(
            "groupConfig",
            CallMethod.RESTPOST,
            {
                "target": group.id if isinstance(group, Group) else group,
                "config": config.dict(exclude_unset=True, exclude_none=True, to_camel=True),
            },
        )

    @ariadne_api
    async def modify_member_info(
        self,
        member: Union[Member, int],
        info: MemberInfo,
        group: Optional[Union[Group, int]] = None,
    ) -> None:
        """
        修改指定群组成员的可修改状态; 需要具有相应权限(管理员/群主).

        Args:
            member (Union[Member, int]): \
                指定的群组成员, 可为 Member 实例, 若前设成立, 则不需要提供 group.
            info (MemberInfo): 已修改的指定群组成员的可修改状态
            group (Optional[Union[Group, int]], optional): \
                如果 member 为 Member 实例, 则不需要提供本项, 否则需要. 默认为 None.

        Raises:
            TypeError: 提供了错误的参数, 阅读有关文档得到问题原因

        Returns:
            None: 没有返回.
        """
        if group is None:
            if isinstance(member, Member):
                group = member.group
            else:
                raise TypeError(
                    "you should give a Member instance if you cannot give a Group instance to me."
                )
        await self.connection.call(
            "memberInfo",
            CallMethod.RESTPOST,
            {
                "target": group.id if isinstance(group, Group) else group,
                "memberId": member.id if isinstance(member, Member) else member,
                "info": info.dict(exclude_none=True, exclude_unset=True),
            },
        )

    @ariadne_api
    async def modify_member_admin(
        self,
        assign: bool,
        member: Union[Member, int],
        group: Optional[Union[Group, int]] = None,
    ) -> None:
        """
        修改一位群组成员管理员权限; 需要有相应权限(群主)

        Args:
            member (Union[Member, int]): 指定群成员, 可为 Member 实例, 若前设成立, 则不需要提供 group.
            assign (bool): 是否设置群成员为管理员.
            group (Optional[Union[Group, int]], optional): \
                如果 member 为 Member 实例, 则不需要提供本项, 否则需要. 默认为 None.

        Raises:
            TypeError: 提供了错误的参数, 阅读有关文档得到问题原因
            PermissionError: 没有相应操作权限.

        Returns:
            None: 没有返回.
        """
        if group is None:
            if isinstance(member, Member):
                group = member.group
            else:
                raise TypeError(
                    "you should give a Member instance if you cannot give a Group instance to me."
                )
        await self.connection.call(
            "memberAdmin",
            CallMethod.POST,
            {
                "target": group.id if isinstance(group, Group) else group,
                "memberId": member.id if isinstance(member, Member) else member,
                "assign": assign,
            },
        )

    @ariadne_api
    async def register_command(
        self, name: str, alias: Iterable[str] = (), usage: str = "", description: str = ""
    ) -> None:
        """注册一个 mirai-console 指令

        Args:
            name (str): 指令名
            alias (Iterable[str], optional): 指令别名. Defaults to ().
            usage (str, optional): 使用方法字符串. Defaults to "".
            description (str, optional): 描述字符串. Defaults to "".

        """
        await self.connection.call(
            "cmd_register",
            CallMethod.POST,
            {
                "name": name,
                "alias": alias,
                "usage": usage,
                "description": description,
            },
        )

    @ariadne_api
    async def execute_command(self, command: Union[str, Iterable[str]]) -> None:
        """执行一条 mirai-console 指令

        Args:
            command (Union[str, Iterable[str]]): 指令字符串.

        """
        if isinstance(command, str):
            command = command.split(" ")
        await self.connection.call(
            "cmd_execute",
            CallMethod.POST,
            {
                "command": command,
            },
        )

    @ariadne_api
    async def get_friend_list(self) -> List[Friend]:
        """获取本实例账号添加的好友列表.

        Returns:
            List[Friend]: 添加的好友.
        """
        result = [
            Friend.parse_obj(i)
            for i in await self.connection.call(
                "friendList",
                CallMethod.GET,
                {},
            )
        ]

        cache_set = self.launch_manager.get_interface(Memcache).set
        await asyncio.gather(
            *(cache_set(f"account.{self.account}.friend.{int(i)}", i, timedelta(seconds=120)) for i in result)
        )
        return result

    @overload
    async def get_friend(
        self, friend_id: int, *, assertion: Literal[False] = False, cache: bool = False
    ) -> Optional[Friend]:
        """从已知的可能的好友 ID, 获取 Friend 实例.

        Args:
            friend_id (int): 已知的可能的好友 ID.
            assertion (bool, optional): 检查是否存在. Defaults to False.
            cache (bool, optional): 是否使用缓存. Defaults to False.

        Returns:
            Friend: 操作成功, 你得到了你应得的.
            None: 未能获取到.
        """
        ...

    @overload
    async def get_friend(self, friend_id: int, *, assertion: Literal[True], cache: bool = False) -> Friend:
        """从已知的可能的好友 ID, 获取 Friend 实例.

        Args:
            friend_id (int): 已知的可能的好友 ID.
            assertion (bool, optional): 检查是否存在. Defaults to False.
            cache (bool, optional): 是否使用缓存. Defaults to False.

        Returns:
            Friend: 操作成功, 你得到了你应得的.
            None: 未能获取到.
        """
        ...

    @ariadne_api
    async def get_friend(
        self, friend_id: int, *, assertion: bool = False, cache: bool = False
    ) -> Optional[Friend]:
        """从已知的可能的好友 ID, 获取 Friend 实例.

        Args:
            friend_id (int): 已知的可能的好友 ID.
            assertion (bool, optional): 检查是否存在. Defaults to False.
            cache (bool, optional): 是否使用缓存. Defaults to False.

        Returns:
            Friend: 操作成功, 你得到了你应得的.
            None: 未能获取到.
        """
        cache_get = self.launch_manager.get_interface(Memcache).get
        key = f"account.{self.account}.friend.{friend_id}"

        if cache and (friend := await cache_get(key)):
            return friend

        await self.get_friend_list()

        if friend := await cache_get(key):
            return friend

        if assertion:
            raise ValueError(f"Friend {friend_id} not found.")

    @ariadne_api
    async def get_group_list(self) -> List[Group]:
        """获取本实例账号加入的群组列表.

        Returns:
            List[Group]: 加入的群组.
        """
        result = [
            Group.parse_obj(i)
            for i in await self.connection.call(
                "groupList",
                CallMethod.GET,
                {},
            )
        ]

        cache_set = self.launch_manager.get_interface(Memcache).set
        await asyncio.gather(
            *(cache_set(f"account.{self.account}.group.{int(i)}", i, timedelta(120)) for i in result)
        )
        return result

    @overload
    async def get_group(
        self, group_id: int, *, assertion: Literal[False] = False, cache: bool = False
    ) -> Optional[Group]:
        """尝试从已知的群组唯一ID, 获取对应群组的信息; 可能返回 None.

        Args:
            group_id (int): 尝试获取的群组的唯一 ID.
            assertion (bool, optional): 是否强制验证. Defaults to False.
            cache (bool, optional): 是否使用缓存. Defaults to False.

        Returns:
            Group: 操作成功, 你得到了你应得的.
            None: 未能获取到.
        """
        ...

    @overload
    async def get_group(self, group_id: int, *, assertion: Literal[True], cache: bool = False) -> Group:
        """尝试从已知的群组唯一ID, 获取对应群组的信息; 可能返回 None.

        Args:
            group_id (int): 尝试获取的群组的唯一 ID.
            assertion (bool, optional): 是否强制验证. Defaults to False.
            cache (bool, optional): 是否使用缓存. Defaults to False.

        Returns:
            Group: 操作成功, 你得到了你应得的.
            None: 未能获取到.
        """
        ...

    @ariadne_api
    async def get_group(
        self, group_id: int, *, assertion: bool = False, cache: bool = False
    ) -> Optional[Group]:
        """尝试从已知的群组唯一ID, 获取对应群组的信息; 可能返回 None.

        Args:
            group_id (int): 尝试获取的群组的唯一 ID.
            assertion (bool, optional): 是否强制验证. Defaults to False.
            cache (bool, optional): 是否使用缓存. Defaults to False.

        Returns:
            Group: 操作成功, 你得到了你应得的.
            None: 未能获取到.
        """
        cache_get = self.launch_manager.get_interface(Memcache).get
        key = f"account.{self.account}.group.{group_id}"

        if cache and (group := await cache_get(key)):
            return group

        await self.get_group_list()

        if group := await cache_get(key):
            return group

        if assertion:
            raise ValueError(f"Group {group_id} not found.")

    @ariadne_api
    async def get_member_list(self, group: Union[Group, int], *, cache: bool = True) -> List[Member]:
        """尝试从已知的群组获取对应成员的列表.

        Args:
            group (Union[Group, int]): 已知的群组
            cache (bool, optional): 是否使用缓存. Defaults to True.

        Returns:
            List[Member]: 群内成员的 Member 对象.
        """
        group_id = int(group)

        result = [
            Member.parse_obj(i)
            for i in await (
                self.connection.call(
                    "memberList",
                    CallMethod.GET,
                    {
                        "target": group_id,
                    },
                )
                if cache
                else self.connection.call(
                    "latestMemberList",
                    CallMethod.GET,
                    {
                        "target": group_id,
                        "memberIds": [],
                    },
                )
            )
        ]

        cache_set = self.launch_manager.get_interface(Memcache).set

        await asyncio.gather(
            cache_set(f"account.{self.account}.group.{group_id}", result[0].group, timedelta(seconds=120)),
            *(
                cache_set(
                    f"account.{self.account}.group.{group_id}.member.{int(i)}", i, timedelta(seconds=120)
                )
                for i in result
            ),
        )

        return result

    @ariadne_api
    async def get_member(self, group: Union[Group, int], member_id: int, *, cache: bool = False) -> Member:
        """尝试从已知的群组唯一 ID 和已知的群组成员的 ID, 获取对应成员的信息.

        Args:
            group (Union[Group, int]): 已知的群组唯一 ID
            member_id (int): 已知的群组成员的 ID
            cache (bool, optional): 是否使用缓存. Defaults to False.

        Returns:
            Member: 对应群成员对象
        """
        interface = self.launch_manager.get_interface(Memcache)
        group_id = int(group)
        key = f"account.{self.account}.group.{group_id}.member.{member_id}"

        if cache and (member := await interface.get(key)):
            return member

        result = Member.parse_obj(
            await self.connection.call(
                "memberInfo",
                CallMethod.RESTGET,
                {
                    "target": group_id,
                    "memberId": member_id,
                },
            )
        )

        await asyncio.gather(
            interface.set(f"account.{self.account}.group.{group_id}", result, timedelta(seconds=120)),
            interface.set(key, result, timedelta(seconds=120)),
        )

        return result

    @ariadne_api
    async def get_bot_profile(self) -> Profile:
        """获取本实例绑定账号的 Profile.

        Returns:
            Profile: 找到的 Profile.
        """
        result = await self.connection.call(
            "botProfile",
            CallMethod.GET,
            {},
        )
        return Profile.parse_obj(result)

    @ariadne_api
    async def get_user_profile(self, target: Union[int, Friend, Member, Stranger]) -> Profile:
        """获取任意 QQ 用户的 Profile. 需要 mirai-api-http 2.5.0+.

        Args:
            target (Union[int, Friend, Member, Stranger]): 任意 QQ 用户.

        Returns:
            Profile: 找到的 Profile.
        """
        result = await self.connection.call(
            "userProfile",
            CallMethod.GET,
            {
                "target": int(target),
            },
        )
        return Profile.parse_obj(result)

    @ariadne_api
    async def get_friend_profile(self, friend: Union[Friend, int]) -> Profile:
        """获取好友的 Profile.

        Args:
            friend (Union[Friend, int]): 查找的好友.

        Returns:
            Profile: 找到的 Profile.
        """
        result = await self.connection.call(
            "friendProfile",
            CallMethod.GET,
            {
                "target": int(friend),
            },
        )
        return Profile.parse_obj(result)

    @ariadne_api
    async def get_member_profile(
        self, member: Union[Member, int], group: Optional[Union[Group, int]] = None
    ) -> Profile:
        """获取群员的 Profile.

        Args:
            member (Union[Member, int]): 群员对象.
            group (Optional[Union[Group, int]], optional): \
                检索的群. 提供 Member 形式的 member 参数后可以不提供.

        Raises:
            ValueError: 没有提供可检索的群 ID.

        Returns:
            Profile: 找到的 Profile 对象.
        """
        member_id = member.id if isinstance(member, Member) else member
        group = group or (member.group if isinstance(member, Member) else None)
        group_id = group.id if isinstance(group, Group) else group
        if not group_id:
            raise ValueError("Missing necessary argument: group")
        result = await self.connection.call(
            "memberProfile",
            CallMethod.GET,
            {
                "target": group_id,
                "memberId": member_id,
            },
        )
        return Profile.parse_obj(result)

    @ariadne_api
    async def get_message_from_id(
        self,
        message: Union[Source, int],
        target: Optional[Union[Friend, Group, Member, Stranger, Client, int]] = None,
    ) -> Union[MessageEvent, ActiveMessage]:
        """从 消息 ID 提取 消息事件.

        Note:
            后端 Mirai HTTP API 版本 >= 2.6.0, 仅指定 message 时,
            将尝试使用缓存获得消息事件或以当前事件来源作为 target.

        Args:
            message (Union[Source, int]): 指定的消息.
            target (Union[Friend, Group, Member, Stranger, Client, int], optional): 指定的好友或群组. \
                message 类型为 Source 或 int 时必需.

        Returns:
            MessageEvent: 提取的事件.
        """

        if tuple(map(int, (await self.get_version(cache=True)).split("."))) >= (2, 6, 0):
            if target is not None:
                pass
            elif event := await self.launch_manager.get_interface(Memcache).get(
                f"account.{self.account}.message.{message}"
            ):
                return event
            elif (
                target := await DispatcherInterface.ctx.get().lookup_param(
                    "target", Optional[Union[Friend, Group, Member, Stranger, Client]], None
                )
            ) is None:
                raise TypeError("get_message_from_id() missing 1 required positional argument: 'target'")

            params = {
                "messageId": int(message),
                "target": self.account if isinstance(target, Client) else int(target),
            }
        else:
            params = {
                "id": int(message),
            }

        return cast(
            Union[MessageEvent, ActiveMessage],
            build_event(await self.connection.call("messageFromId", CallMethod.GET, params)),
        )

    @ariadne_api
    async def send_friend_message(
        self,
        target: Union[Friend, int],
        message: MessageContainer,
        *,
        quote: Optional[Union[Source, int]] = None,
        action: Union[SendMessageActionProtocol, Literal[Sentinel], None] = Sentinel,
    ) -> ActiveFriendMessage:
        """发送消息给好友, 可以指定回复的消息.

        Args:
            target (Union[Friend, int]): 指定的好友
            message (MessageContainer): 有效的消息容器.
            quote (Optional[Union[Source, int]], optional): 需要回复的消息, 不要忽视我啊喂?!!, 默认为 None.

        Returns:
            ActiveFriendMessage: 即当前会话账号所发出消息的事件, 可用于回复.
        """
        from .event.message import ActiveFriendMessage

        message = MessageChain(message)
        if isinstance(quote, MessageChain):
            raise TypeError(
                "Using MessageChain as quote target is removed! Get a `Source` from event instead!"
            )

        if action is not None:  # TODO: REFACTOR
            return cast(
                ActiveFriendMessage,
                await self.send_message(
                    (
                        await self.get_friend(target, assertion=True, cache=True)
                        if isinstance(target, int)
                        else target
                    ),
                    message,
                    quote=quote or False,
                    action=action,
                ),
            )

        if isinstance(quote, Source):
            quote = quote.id

        with enter_message_send_context(UploadMethod.Friend):
            message = message.as_sendable()
            try:
                result = await self.connection.call(
                    "sendFriendMessage",
                    CallMethod.POST,
                    {
                        "target": int(target),
                        "messageChain": message.dict()["__root__"],
                        **({"quote": quote} if quote else {}),
                    },
                )
                event = ActiveFriendMessage(
                    messageChain=MessageChain(message),
                    source=Source(id=result["messageId"], time=datetime.now()),
                    subject=(await self.get_friend(int(target), assertion=True, cache=True)),
                )
                with enter_context(self, event):
                    await self.log_config.log(self, event)
                    self.service.broadcast.postEvent(event)
                if result["messageId"] < 0:
                    logger.warning("Failed to send message, your account may be blocked.")
                return event
            except UnknownTarget:
                await self.launch_manager.get_interface(Memcache).delete(
                    f"account.{self.account}.friend.{int(target)}"
                )
                raise

    @ariadne_api
    async def send_group_message(
        self,
        target: Union[Group, Member, int],
        message: MessageContainer,
        *,
        quote: Optional[Union[Source, int]] = None,
        action: Union[SendMessageActionProtocol, Literal[Sentinel], None] = Sentinel,
    ) -> ActiveGroupMessage:
        """发送消息到群组内, 可以指定回复的消息.

        Args:
            target (Union[Group, Member, int]): 指定的群组, 可以是群组的 ID 也可以是 Group 或 Member 实例.
            message (MessageContainer): 有效的消息容器.
            quote (Optional[Union[Source, int]], optional): 需要回复的消息, 不要忽视我啊喂?!!, 默认为 None.
            action (SendMessageActionProtocol, optional): 消息发送的处理 action

        Returns:
            ActiveGroupMessage: 即当前会话账号所发出消息的事件, 可用于回复.
        """
        from .event.message import ActiveGroupMessage

        message = MessageChain(message)
        if isinstance(target, Member):
            target = target.group

        if action is not None:  # TODO: REFACTOR
            return cast(
                ActiveGroupMessage,
                await self.send_message(
                    (
                        await self.get_group(target, assertion=True, cache=True)
                        if isinstance(target, int)
                        else target
                    ),
                    message,
                    quote=quote or False,
                    action=action,
                ),
            )

        if isinstance(quote, MessageChain):
            raise TypeError(
                "Using MessageChain as quote target is removed! Get a `Source` from event instead!"
            )

        if isinstance(quote, Source):
            quote = quote.id

        with enter_message_send_context(UploadMethod.Group):
            message = message.as_sendable().copy()
            try:
                result = await self.connection.call(
                    "sendGroupMessage",
                    CallMethod.POST,
                    {
                        "target": int(target),
                        "messageChain": message.dict()["__root__"],
                        **({"quote": quote} if quote else {}),
                    },
                )
                event = ActiveGroupMessage(
                    messageChain=MessageChain(message),
                    source=Source(id=result["messageId"], time=datetime.now()),
                    subject=(await self.get_group(int(target), assertion=True, cache=True)),
                )
                with enter_context(self, event):
                    await self.log_config.log(self, event)
                    self.service.broadcast.postEvent(event)
                if result["messageId"] < 0:
                    logger.warning("Failed to send message, your account may be blocked.")
                return event
            except UnknownTarget:
                await self.launch_manager.get_interface(Memcache).delete(
                    f"account.{self.account}.group.{int(target)}"
                )
                raise

    @ariadne_api
    async def send_temp_message(
        self,
        target: Union[Member, int],
        message: MessageContainer,
        group: Optional[Union[Group, int]] = None,
        *,
        quote: Optional[Union[Source, int]] = None,
        action: Union[SendMessageActionProtocol, Literal[Sentinel], None] = Sentinel,
    ) -> ActiveTempMessage:
        """发送临时会话给群组中的特定成员, 可指定回复的消息.

        Warning:
            本 API 大概率会导致账号风控/冻结. 请谨慎使用.

        Args:
            group (Union[Group, int]): 指定的群组, 可以是群组的 ID 也可以是 Group 实例.
            target (Union[Member, int]): 指定的群组成员, 可以是成员的 ID 也可以是 Member 实例.
            message (MessageContainer): 有效的消息容器.
            quote (Optional[Union[Source, int]], optional): 需要回复的消息, 不要忽视我啊喂?!!, 默认为 None.
            action (SendMessageActionProtocol, optional): 消息发送的处理 action

        Returns:
            ActiveTempMessage: 即当前会话账号所发出消息的事件, 可用于回复.
        """
        from .event.message import ActiveTempMessage

        message = MessageChain(message)

        if isinstance(quote, MessageChain):
            raise TypeError(
                "Using MessageChain as quote target is removed! Get a `Source` from event instead!"
            )

        new_msg = message.copy().as_sendable()
        group = target.group if (isinstance(target, Member) and not group) else group
        if not group:
            raise ValueError("Missing necessary argument: group")

        if action is not None:  # TODO: REFACTOR
            return cast(
                ActiveTempMessage,
                await self.send_message(
                    await self.get_member(group, target, cache=True) if isinstance(target, int) else target,
                    message,
                    quote=quote or False,
                    action=action,
                ),
            )

        if isinstance(quote, Source):
            quote = quote.id

        with enter_message_send_context(UploadMethod.Temp):
            try:
                result = await self.connection.call(
                    "sendTempMessage",
                    CallMethod.POST,
                    {
                        "group": int(group),
                        "qq": int(target),
                        "messageChain": new_msg.dict()["__root__"],
                        **({"quote": quote} if quote else {}),
                    },
                )
                event: ActiveTempMessage = ActiveTempMessage(
                    messageChain=MessageChain(message),
                    source=Source(id=result["messageId"], time=datetime.now()),
                    subject=(await self.get_member(int(group), int(target), cache=True)),
                )
                with enter_context(self, event):
                    await self.log_config.log(self, event)
                    self.service.broadcast.postEvent(event)
                if result["messageId"] < 0:
                    logger.warning("Failed to send message, your account may be limited.")
                return event
            except UnknownTarget:
                await self.launch_manager.get_interface(Memcache).delete(
                    f"account.{self.account}.group.{int(group)}.member.{int(target)}"
                )
                raise

    @overload
    async def send_message(
        self,
        target: Union[MessageEvent, Group, Friend, Member],
        message: MessageContainer,
        *,
        quote: Union[bool, int, Source, MessageChain] = False,
        action: SendMessageActionProtocol["T"],
    ) -> "T":
        """
        依据传入的 `target` 自动发送消息.

        请注意发送给群成员时会自动作为临时消息发送.

        Args:
            target (Union[MessageEvent, Group, Friend, Member]): 消息发送目标.
            message (Union[MessageChain, List[Union[Element, str]], str]): 要发送的消息链.
            quote (Union[bool, int, Source]): 若为布尔类型, 则会尝试通过传入对象解析要回复的消息, \
            否则会视为 `messageId` 处理.
            action (SendMessageCaller[T], optional): 消息发送的处理 action, \
            可以在 graia.ariadne.util.send 查看自带的 action, \
            未传入使用默认 action

        Returns:
            Union[T, R]: 默认实现为 ActiveMessage
        """
        ...

    @overload
    async def send_message(
        self,
        target: Union[MessageEvent, Group, Friend, Member],
        message: MessageContainer,
        *,
        quote: Union[bool, int, Source, MessageChain] = False,
        action: Literal[Sentinel] = Sentinel,
    ) -> ActiveMessage:
        """
        依据传入的 `target` 自动发送消息.

        请注意发送给群成员时会自动作为临时消息发送.

        Args:
            target (Union[MessageEvent, Group, Friend, Member]): 消息发送目标.
            message (Union[MessageChain, List[Union[Element, str]], str]): 要发送的消息链.
            quote (Union[bool, int, Source]): 若为布尔类型, 则会尝试通过传入对象解析要回复的消息, \
            否则会视为 `messageId` 处理.
            action (SendMessageCaller[T], optional): 消息发送的处理 action, \
            可以在 graia.ariadne.util.send 查看自带的 action, \
            未传入使用默认 action

        Returns:
            Union[T, R]: 默认实现为 ActiveMessage
        """
        ...

    @ariadne_api
    async def send_message(
        self,
        target: Union[MessageEvent, Group, Friend, Member],
        message: MessageContainer,
        *,
        quote: Union[bool, int, Source] = False,
        action: Union[SendMessageActionProtocol["T"], Literal[Sentinel]] = Sentinel,
    ) -> "T":
        """
        依据传入的 `target` 自动发送消息.

        请注意发送给群成员时会自动作为临时消息发送.

        Args:
            target (Union[MessageEvent, Group, Friend, Member]): 消息发送目标.
            message (Union[MessageChain, List[Union[Element, str]], str]): 要发送的消息链.
            quote (Union[bool, int, Source]): 若为布尔类型, 则会尝试通过传入对象解析要回复的消息, \
            否则会视为 `messageId` 处理.
            action (SendMessageCaller[T], optional): 消息发送的处理 action, \
            可以在 graia.ariadne.util.send 查看自带的 action, \
            未传入使用默认 action

        Returns:
            Union[T, R]: 默认实现为 ActiveMessage
        """
        action = action if action is not Sentinel else self.default_send_action
        data: Dict[Any, Any] = {"message": MessageChain(message)}
        # quote
        if isinstance(quote, bool):
            if quote:
                if isinstance(target, MessageEvent):
                    data["quote"] = target.source
                else:
                    raise TypeError("Passing `quote=True` is only valid when passing a MessageEvent.")
        elif isinstance(quote, (int, Source)):
            data["quote"] = quote
        elif isinstance(quote, MessageChain):
            raise TypeError(
                "Using MessageChain as quote target is removed! Get a `Source` from event instead!"
            )
        # target: MessageEvent
        if isinstance(target, GroupMessage):
            data["target"] = target.sender.group
        elif isinstance(target, (FriendMessage, TempMessage)):
            data["target"] = target.sender
        else:  # target: sender
            data["target"] = target
        send_data: SendMessageDict = SendMessageDict(**data)
        # send message
        data = await action.param(send_data)  # type: ignore

        try:
            if isinstance(data["target"], Friend):
                val = await self.send_friend_message(**data, action=None)
            elif isinstance(data["target"], Group):
                val = await self.send_group_message(**data, action=None)
            elif isinstance(data["target"], Member):
                val = await self.send_temp_message(**data, action=None)
            else:
                logger.warning(
                    f"Unable to send {data['message']} to {data['target']} of type {type(data['target'])}"
                )
                return await action.result(
                    ActiveMessage(
                        type="Unknown",
                        messageChain=MessageChain(data["message"]),
                        source=Source(id=-1, time=datetime.now()),
                        subject=data["target"],
                    )
                )
        except SendMessageException as e:
            e.send_data = send_data  # type: ignore
            return await action.exception(e)
        else:
            return await action.result(val)

    @ariadne_api
    async def send_nudge(
        self, target: Union[Friend, Member, int], group: Optional[Union[Group, int]] = None
    ) -> None:
        """
        向指定的群组成员或好友发送戳一戳消息.

        Args:
            target (Union[Friend, Member]): 发送戳一戳的目标.
            group (Union[Group, int], optional): 发送的群组.

        Returns:
            None: 没有返回.
        """
        target_id = target if isinstance(target, int) else target.id

        subject_id = (group.id if isinstance(group, Group) else group) or (
            target.group.id if isinstance(target, Member) else target_id
        )
        kind = "Group" if group or isinstance(target, Member) else "Friend"
        await self.connection.call(
            "sendNudge",
            CallMethod.POST,
            {
                "target": target_id,
                "subject": subject_id,
                "kind": kind,
            },
        )

    @ariadne_api
    async def recall_message(
        self,
        message: Union[MessageEvent, ActiveMessage, Source, int],
        target: Optional[Union[Friend, Group, Member, Stranger, Client, int]] = None,
    ) -> None:
        """撤回指定的消息;
        撤回自己的消息需要在发出后 2 分钟内才能成功撤回;
        如果在群组内, 需要撤回他人的消息则需要管理员/群主权限.

        Note:
            后端 Mirai HTTP API 版本 >= 2.6.0, 仅指定 message 且类型为 Source 或 int 时, \
                将尝试使用缓存获得消息事件或以当前事件来源作为 target.

        Args:
            message (Union[MessageEvent, ActiveMessage, Source, int]): 指定的消息.
            target (Union[Friend, Group, Member, Stranger, Client, int], optional): 指定的好友或群组. \
                message 类型为 Source 或 int 时必需.

        Returns:
            None: 没有返回
        """
        if target is not None:
            pass
        elif isinstance(message, GroupMessage):
            target = message.sender.group
        elif isinstance(message, MessageEvent):
            target = message.sender
        elif isinstance(message, ActiveMessage):
            target = message.subject

        if tuple(map(int, (await self.get_version(cache=True)).split("."))) >= (2, 6, 0):
            if target is not None:
                pass
            elif event := await self.launch_manager.get_interface(Memcache).get(
                f"account.{self.account}.message.{int(message)}"
            ):
                return await self.recall_message(event)
            elif (
                target := await DispatcherInterface.ctx.get().lookup_param(
                    "target", Union[Friend, Group, Member, Stranger, Client, None], None
                )
            ) is None:
                raise TypeError("recall_message() missing 1 required positional argument: 'target'")

            params = {
                "messageId": int(message),
                "target": self.account if isinstance(target, Client) else int(target),
            }
        else:
            params = {
                "target": int(message),
            }

        await self.connection.call("recall", CallMethod.POST, params)

    @ariadne_api
    async def get_roaming_message(
        self, start: datetime, end: datetime, target: Union[Friend, int]
    ) -> List[FriendMessage]:
        """获取漫游消息. 需要 Mirai API HTTP 2.6.0+.

        Args:
            start (datetime): 起始时间.
            end (datetime): 结束时间.
            target (Union[Friend, int]): 漫游消息对象.

        Returns:
            List[FriendMessage]: 漫游消息列表.
        """
        target = target if isinstance(target, int) else target.id
        result = await self.connection.call(
            "roamingMessages",
            CallMethod.POST,
            {
                "target": target,
                "start": start.timestamp(),
                "end": end.timestamp(),
            },
        )

        return [FriendMessage.parse_obj(i) for i in result]
