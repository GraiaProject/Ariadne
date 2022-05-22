"""Ariadne 实例
"""

import asyncio
import base64
import inspect
import io
import os
import sys
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
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

from graia.amnesia.launch.manager import LaunchManager
from graia.broadcast import Broadcast
from loguru import logger
from typing_extensions import Self

from .connection import ConnectionInterface
from .connection._info import U_Info
from .connection.util import CallMethod, UploadMethod, build_event
from .context import enter_context, enter_message_send_context
from .event import MiraiEvent
from .event.message import FriendMessage, GroupMessage, MessageEvent, TempMessage
from .event.mirai import FriendEvent, GroupEvent
from .message.chain import MessageChain
from .message.element import Source
from .model import (
    Announcement,
    BotMessage,
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
from .service import ElizabethService
from .typing import SendMessageActionProtocol, SendMessageDict, SendMessageException, T
from .util import app_ctx_manager

if TYPE_CHECKING:
    from .message.element import Image, Voice


class Ariadne:
    service: ClassVar[ElizabethService] = ElizabethService()
    launch_manager: ClassVar[LaunchManager] = LaunchManager()
    _launch_task: ClassVar[Optional[asyncio.Task]] = None
    instances: ClassVar[Dict[int, "Ariadne"]] = {}
    default_account: ClassVar[Optional[int]] = None
    default_send_action: SendMessageActionProtocol
    held_objects: ClassVar[Dict[type, Any]] = {
        Broadcast: service.broadcast,
        asyncio.AbstractEventLoop: service.loop,
    }

    def __new__(
        cls: type[Self],
        connection: Union[Iterable[U_Info], int] = (),
        log_config: Optional[LogConfig] = None,
    ) -> Self:
        if isinstance(connection, int):
            assert connection in Ariadne.service.connections, f"{connection} is not configured"
            assert log_config is None, "You can't reconfigure existing instance"
            return cls.instances[connection]
        return super().__new__(cls)

    def __init__(
        self,
        connection: Union[Iterable[U_Info], int] = (),
        log_config: Optional[LogConfig] = None,
    ) -> None:
        from .util.send import Strict

        if isinstance(connection, int):
            return
        self.default_send_action = Strict
        account = Ariadne.service.add_configs(connection)[1]
        assert account not in Ariadne.instances, "You can't configure an account twice!"
        Ariadne.instances[account] = self
        self.account: int = account
        assert account in Ariadne.service.connections, f"{account} is not configured"
        self.connection: ConnectionInterface = Ariadne.service.get_interface(ConnectionInterface).bind(
            account
        )
        self.log_config: LogConfig = log_config or LogConfig()
        self.connection.add_callback(self.log_config.event_hook(self))
        self.connection.add_callback(self._event_hook)

    async def _event_hook(self, event: MiraiEvent):
        with enter_context(self, event):
            sys.audit("AriadnePostRemoteEvent", event)
            if isinstance(event, MessageEvent) and event.messageChain.onlyContains(Source):
                event.messageChain.append("<! 不支持的消息类型 !>")
            if isinstance(event, FriendEvent):
                with enter_message_send_context(UploadMethod.Friend):
                    self.service.broadcast.postEvent(event)
            elif isinstance(event, GroupEvent):
                with enter_message_send_context(UploadMethod.Group):
                    self.service.broadcast.postEvent(event)
            else:
                self.service.broadcast.postEvent(event)

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
        if cls._launch_task is None or cls._launch_task.done():
            cls._launch_task = asyncio.create_task(cls.launch_manager.launch(), name="amnesia-launch")

    @classmethod
    async def lifecycle(cls) -> None:
        if cls._launch_task is None or cls._launch_task.done():
            await cls.launch()
        if cls._launch_task is not None and not cls._launch_task.done():
            await cls._launch_task

    @classmethod
    def stop(cls) -> None:
        if cls._launch_task is not None and not cls._launch_task.done():
            cls._launch_task.cancel()

    @classmethod
    def launch_blocking(cls):
        cls._patch_launch_manager()
        cls.launch_manager.launch_blocking(loop=cls.service.loop)

    @classmethod
    def create(cls, typ: Type[T], reuse: bool = True) -> T:
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

        obj: T = typ(*call_args, **call_kwargs)
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
        return cls(cls.default_account)

    def __getattr__(self, snake_case_name: str) -> Callable:
        # snake_case to camelCase
        snake_segments = snake_case_name.split("_")
        camel_case_name = snake_segments[0] + "".join(s.capitalize() for s in snake_segments[1:])
        return self.__dict__[camel_case_name]

    @app_ctx_manager
    async def getVersion(self) -> str:
        """获取后端 Mirai HTTP API 版本.

        Returns:
            str: 版本信息.
        """
        result = await self.connection._call("about", CallMethod.GET, {})
        return result["version"]

    async def getFileIterator(
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
            cache = await self.getFileList(target, id, current_offset, size, with_download_info)
            current_offset += len(cache)
            if not cache:
                return

    @app_ctx_manager
    async def getFileList(
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

    @app_ctx_manager
    async def getFileInfo(
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

    @app_ctx_manager
    async def makeDirectory(
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
                "name": name,
                "target": target,
            },
        )

        return FileInfo.parse_obj(result)

    @app_ctx_manager
    async def deleteFile(
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

    @app_ctx_manager
    async def moveFile(
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
            "file/move",
            CallMethod.POST,
            {
                "id": id,
                "target": target,
                "moveTo": dest_id,
            },
        )

    @app_ctx_manager
    async def renameFile(
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

    @app_ctx_manager
    async def uploadFile(
        self,
        data: Union[bytes, io.IOBase, os.PathLike],
        method: Union[str, UploadMethod, None] = None,
        target: Union[Friend, Group, int] = -1,
        path: str = "",
        name: str = "",
    ) -> "FileInfo":
        """
        上传文件到指定目标, 需要提供: 文件的原始数据(bytes), 文件的上传类型,
        上传目标, (可选)上传目录ID.
        Args:
            data (Union[bytes, io.IOBase, os.PathLike]): 文件的原始数据
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
                "file": (data, {"filename": name} if name else {}),
            },
        )

        return FileInfo.parse_obj(result)

    @app_ctx_manager
    async def uploadImage(
        self, data: Union[bytes, io.IOBase, os.PathLike], method: Union[None, str, UploadMethod] = None
    ) -> "Image":
        """上传一张图片到远端服务器, 需要提供: 图片的原始数据(bytes), 图片的上传类型.
        Args:
            data (Union[bytes, io.IOBase, os.PathLike]): 图片的原始数据
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

    @app_ctx_manager
    async def uploadVoice(
        self, data: Union[bytes, io.IOBase, os.PathLike], method: Union[None, str, UploadMethod] = None
    ) -> "Voice":
        """上传语音到远端服务器, 需要提供: 语音的原始数据(bytes), 语音的上传类型.
        Args:
            data (Union[bytes, io.IOBase, os.PathLike]): 语音的原始数据
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

    async def getAnnouncementIterator(
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
            cache = await self.getAnnouncementList(target, current_offset, size)
            current_offset += len(cache)
            if not cache:
                return

    @app_ctx_manager
    async def getAnnouncementList(
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

    @app_ctx_manager
    async def publishAnnouncement(
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

    @app_ctx_manager
    async def deleteAnnouncement(self, target: Union[Group, int], anno: Union[Announcement, int]) -> None:
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

    @app_ctx_manager
    async def deleteFriend(self, target: Union[Friend, int]) -> None:
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

    @app_ctx_manager
    async def muteMember(self, group: Union[Group, int], member: Union[Member, int], time: int) -> None:
        """
        在指定群组禁言指定群成员; 需要具有相应权限(管理员/群主); `time` 不得大于 `30*24*60*60=2592000` 或小于 `0`, 否则会自动修正;
        当 `time` 小于等于 `0` 时, 不会触发禁言操作; 禁言对象极有可能触发 `PermissionError`, 在这之前请对其进行判断!

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

    @app_ctx_manager
    async def unmuteMember(self, group: Union[Group, int], member: Union[Member, int]) -> None:
        """
        在指定群组解除对指定群成员的禁言; 需要具有相应权限(管理员/群主); 对象极有可能触发 `PermissionError`, 在这之前请对其进行判断!

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

    @app_ctx_manager
    async def muteAll(self, group: Union[Group, int]) -> None:
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

    @app_ctx_manager
    async def unmuteAll(self, group: Union[Group, int]) -> None:
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

    @app_ctx_manager
    async def kickMember(
        self, group: Union[Group, int], member: Union[Member, int], message: str = ""
    ) -> None:
        """
        将目标群组成员从指定群组踢出; 需要具有相应权限(管理员/群主)

        Args:
            group (Union[Group, int]): 指定的群组
            member (Union[Member, int]): 指定的群成员(只能是普通群员或者是管理员, 后者则要求群主权限)
            message (str, optional): 对踢出对象要展示的消息

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
            },
        )

    @app_ctx_manager
    async def quitGroup(self, group: Union[Group, int]) -> None:
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

    @app_ctx_manager
    async def setEssence(self, target: Union[Source, BotMessage, int]) -> None:
        """
        添加指定消息为群精华消息; 需要具有相应权限(管理员/群主).
        请自行判断消息来源是否为群组.

        Args:
            target (Union[Source, BotMessage, int]): 特定信息的 `messageId`, \
            可以是 `Source` 实例, `BotMessage` 实例或者是单纯的 int 整数.

        Returns:
            None: 没有返回.
        """
        if isinstance(target, BotMessage):
            target = target.messageId
        elif isinstance(target, Source):
            target = target.id

        await self.connection.call(
            "setEssence",
            CallMethod.POST,
            {"target": target},
        )

    @app_ctx_manager
    async def getGroupConfig(self, group: Union[Group, int]) -> GroupConfig:
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

        return GroupConfig.parse_obj(result)

    @app_ctx_manager
    async def modifyGroupConfig(self, group: Union[Group, int], config: GroupConfig) -> None:
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
                "config": config.dict(exclude_unset=True, exclude_none=True),
            },
        )

    @app_ctx_manager
    async def modifyMemberInfo(
        self,
        member: Union[Member, int],
        info: MemberInfo,
        group: Optional[Union[Group, int]] = None,
    ) -> None:
        """
        修改指定群组成员的可修改状态; 需要具有相应权限(管理员/群主).

        Args:
            member (Union[Member, int]): 指定的群组成员, 可为 Member 实例, 若前设成立, 则不需要提供 group.
            info (MemberInfo): 已修改的指定群组成员的可修改状态
            group (Optional[Union[Group, int]], optional): 如果 member 为 Member 实例, 则不需要提供本项, 否则需要. 默认为 None.

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
                "info": info.dict(exclude_none=True, exclude_unset=True, by_alias=True),
            },
        )

    @app_ctx_manager
    async def modifyMemberAdmin(
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
            group (Optional[Union[Group, int]], optional): 如果 member 为 Member 实例, 则不需要提供本项, 否则需要. 默认为 None.

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

    @app_ctx_manager
    async def registerCommand(
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

    @app_ctx_manager
    async def executeCommand(self, command: Union[str, Iterable[str]]) -> None:
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

    @app_ctx_manager
    async def getFriendList(self) -> List[Friend]:
        """获取本实例账号添加的好友列表.

        Returns:
            List[Friend]: 添加的好友.
        """
        result = await self.connection.call(
            "friendList",
            CallMethod.GET,
            {},
        )
        return [Friend.parse_obj(i) for i in result]

    @overload
    async def getFriend(self, friend_id: int, assertion: Literal[False] = False) -> Optional[Friend]:
        ...

    @overload
    async def getFriend(self, friend_id: int, assertion: Literal[True]) -> Friend:
        ...

    @app_ctx_manager
    async def getFriend(self, friend_id: int, assertion: bool = False) -> Optional[Friend]:
        """从已知的可能的好友 ID, 获取 Friend 实例.

        Args:
            friend_id (int): 已知的可能的好友 ID.

        Returns:
            Friend: 操作成功, 你得到了你应得的.
            None: 未能获取到.
        """
        data = await self.getFriendList()
        for i in data:
            if i.id == friend_id:
                return i
        if assertion:
            raise ValueError(f"Friend {friend_id} not found.")

    @app_ctx_manager
    async def getGroupList(self) -> List[Group]:
        """获取本实例账号加入的群组列表.

        Returns:
            List[Group]: 加入的群组.
        """
        result = await self.connection.call(
            "groupList",
            CallMethod.GET,
            {},
        )
        return [Group.parse_obj(i) for i in result]

    @overload
    async def getGroup(self, group_id: int, assertion: Literal[False] = False) -> Optional[Group]:
        ...

    @overload
    async def getGroup(self, group_id: int, assertion: Literal[True]) -> Group:
        ...

    @app_ctx_manager
    async def getGroup(self, group_id: int, assertion: bool = False) -> Optional[Group]:
        """尝试从已知的群组唯一ID, 获取对应群组的信息; 可能返回 None.

        Args:
            group_id (int): 尝试获取的群组的唯一 ID.
            assertion (bool, optional): 是否强制验证. Defaults to False.

        Returns:
            Group: 操作成功, 你得到了你应得的.
            None: 未能获取到.
        """
        data = await self.getGroupList()
        for i in data:
            if i.id == group_id:
                return i
        if assertion:
            raise ValueError(f"Group {group_id} not found.")

    @app_ctx_manager
    async def getMemberList(self, group: Union[Group, int]) -> List[Member]:
        """尝试从已知的群组获取对应成员的列表.

        Args:
            group (Union[Group, int]): 已知的群组

        Returns:
            List[Member]: 群内成员的 Member 对象.
        """
        result = await self.connection.call(
            "memberList",
            CallMethod.GET,
            {
                "target": group.id if isinstance(group, Group) else group,
            },
        )
        return [Member.parse_obj(i) for i in result]

    @app_ctx_manager
    async def getMember(self, group: Union[Group, int], member_id: int) -> Member:
        """尝试从已知的群组唯一 ID 和已知的群组成员的 ID, 获取对应成员的信息.

        Args:
            group (Union[Group, int]): 已知的群组唯一 ID
            member_id (int): 已知的群组成员的 ID

        Returns:
            Member: 对应群成员对象
        """
        result = await self.connection.call(
            "memberInfo",
            CallMethod.RESTGET,
            {
                "target": group.id if isinstance(group, Group) else group,
                "memberId": member_id,
            },
        )

        return Member.parse_obj(result)

    @app_ctx_manager
    async def getBotProfile(self) -> Profile:
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

    @app_ctx_manager
    async def getUserProfile(self, target: Union[int, Friend, Member, Stranger]) -> Profile:
        """获取任意 QQ 用户的 Profile.

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

    @app_ctx_manager
    async def getFriendProfile(self, friend: Union[Friend, int]) -> Profile:
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

    @app_ctx_manager
    async def getMemberProfile(
        self, member: Union[Member, int], group: Optional[Union[Group, int]] = None
    ) -> Profile:
        """获取群员的 Profile.

        Args:
            member (Union[Member, int]): 群员对象.
            group (Optional[Union[Group, int]], optional): 检索的群. 提供 Member 形式的 member 参数后可以不提供.

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

    @app_ctx_manager
    async def getMessageFromId(self, messageId: int) -> MessageEvent:
        """从 消息 ID 提取 消息事件.

        Args:
            messageId (int): 消息 ID.

        Returns:
            MessageEvent: 提取的事件.
        """
        result = await self.connection.call(
            "messageFromId",
            CallMethod.GET,
            {
                "id": messageId,
            },
        )
        return cast(MessageEvent, build_event(result))

    @app_ctx_manager
    async def sendFriendMessage(
        self,
        target: Union[Friend, int],
        message: MessageChain,
        *,
        quote: Optional[Union[Source, int]] = None,
    ) -> BotMessage:
        """发送消息给好友, 可以指定回复的消息.

        Args:
            target (Union[Friend, int]): 指定的好友
            message (MessageChain): 有效的, 可发送的(Sendable)消息链.
            quote (Optional[Union[Source, int]], optional): 需要回复的消息, 不要忽视我啊喂?!!, 默认为 None.

        Returns:
            BotMessage: 即当前会话账号所发出消息的元数据, 内包含有一 `messageId` 属性, 可用于回复.
        """
        from .event.message import ActiveFriendMessage

        with enter_message_send_context(UploadMethod.Friend):
            new_msg = message.copy()
            new_msg.prepare()
            result = await self.connection.call(
                "sendFriendMessage",
                CallMethod.POST,
                {
                    "target": int(target),
                    "messageChain": new_msg.dict()["__root__"],
                    **({"quote": quote.id if isinstance(quote, Source) else quote} if quote else {}),
                },
            )
            event: ActiveFriendMessage = ActiveFriendMessage(
                messageChain=MessageChain([Source(id=result["messageId"], time=datetime.now())]) + message,
                subject=(await self.getFriend(int(target), assertion=True)),
            )
            with enter_context(self, event):
                await self.log_config.log(self, event)
                self.service.broadcast.postEvent(event)
            if result["messageId"] < 0:
                logger.warning("Failed to send message, your account may be blocked.")
            return BotMessage(messageId=result["messageId"], origin=message)

    @app_ctx_manager
    async def sendGroupMessage(
        self,
        target: Union[Group, Member, int],
        message: MessageChain,
        *,
        quote: Optional[Union[Source, int]] = None,
    ) -> BotMessage:
        """发送消息到群组内, 可以指定回复的消息.

        Args:
            target (Union[Group, Member, int]): 指定的群组, 可以是群组的 ID 也可以是 Group 或 Member 实例.
            message (MessageChain): 有效的, 可发送的(Sendable)消息链.
            quote (Optional[Union[Source, int]], optional): 需要回复的消息, 不要忽视我啊喂?!!, 默认为 None.

        Returns:
            BotMessage: 即当前会话账号所发出消息的元数据, 内包含有一 `messageId` 属性, 可用于回复.
        """
        from .event.message import ActiveGroupMessage

        if isinstance(target, Member):
            target = target.group

        with enter_message_send_context(UploadMethod.Group):
            new_msg = message.copy()
            new_msg.prepare()
            result = await self.connection.call(
                "sendGroupMessage",
                CallMethod.POST,
                {
                    "target": int(target),
                    "messageChain": new_msg.dict()["__root__"],
                    **({"quote": quote.id if isinstance(quote, Source) else quote} if quote else {}),
                },
            )
            event: ActiveGroupMessage = ActiveGroupMessage(
                messageChain=MessageChain([Source(id=result["messageId"], time=datetime.now())]) + message,
                subject=(await self.getGroup(int(target), assertion=True)),
            )
            with enter_context(self, event):
                await self.log_config.log(self, event)
                self.service.broadcast.postEvent(event)
            if result["messageId"] < 0:
                logger.warning("Failed to send message, your account may be blocked.")
            return BotMessage(messageId=result["messageId"], origin=message)

    @app_ctx_manager
    async def sendTempMessage(
        self,
        target: Union[Member, int],
        message: MessageChain,
        group: Optional[Union[Group, int]] = None,
        *,
        quote: Optional[Union[Source, int]] = None,
    ) -> BotMessage:
        """发送临时会话给群组中的特定成员, 可指定回复的消息.

        Warning:
            本 API 大概率会导致账号风控/冻结. 请谨慎使用.

        Args:
            group (Union[Group, int]): 指定的群组, 可以是群组的 ID 也可以是 Group 实例.
            target (Union[Member, int]): 指定的群组成员, 可以是成员的 ID 也可以是 Member 实例.
            message (MessageChain): 有效的, 可发送的(Sendable)消息链.
            quote (Optional[Union[Source, int]], optional): 需要回复的消息, 不要忽视我啊喂?!!, 默认为 None.

        Returns:
            BotMessage: 即当前会话账号所发出消息的元数据, 内包含有一 `messageId` 属性, 可用于回复.
        """
        from .event.message import ActiveTempMessage

        new_msg = message.copy()
        new_msg.prepare()
        group = target.group if (isinstance(target, Member) and not group) else group
        if not group:
            raise ValueError("Missing necessary argument: group")
        with enter_message_send_context(UploadMethod.Temp):
            result = await self.connection.call(
                "sendTempMessage",
                CallMethod.POST,
                {
                    "group": int(group),
                    "qq": int(target),
                    "messageChain": new_msg.dict()["__root__"],
                    **({"quote": quote.id if isinstance(quote, Source) else quote} if quote else {}),
                },
            )
            event: ActiveTempMessage = ActiveTempMessage(
                messageChain=MessageChain([Source(id=result["messageId"], time=datetime.now())]) + message,
                subject=(await self.getMember(int(group), int(target))),
            )
            with enter_context(self, event):
                await self.log_config.log(self, event)
                self.service.broadcast.postEvent(event)
            if result["messageId"] < 0:
                logger.warning("Failed to send message, your account may be limited.")
            return BotMessage(messageId=result["messageId"], origin=message)

    @app_ctx_manager
    async def sendMessage(
        self,
        target: Union[MessageEvent, Group, Friend, Member],
        message: MessageChain,
        *,
        quote: Union[bool, int, Source, MessageChain] = False,
        action: SendMessageActionProtocol["T"] = ...,
    ) -> "T":
        """
        依据传入的 `target` 自动发送消息.
        请注意发送给群成员时会自动作为临时消息发送.

        Args:
            target (Union[MessageEvent, Group, Friend, Member]): 消息发送目标.
            message (MessageChain): 要发送的消息链.
            quote (Union[bool, int, Source]): 若为布尔类型, 则会尝试通过传入对象解析要回复的消息, \
            否则会视为 `messageId` 处理.
            action (SendMessageCaller[T], optional): 消息发送的处理 action, \
            可以在 graia.ariadne.util.send 查看自带的 action, \
            未传入使用默认 action

        Returns:
            Union[T, R]: 默认实现为 BotMessage
        """
        action = action if action is not ... else self.default_send_action
        data: Dict[Any, Any] = {"message": message}
        # quote
        if isinstance(quote, bool) and quote and isinstance(target, MessageEvent):
            data["quote"] = target.messageChain.getFirst(Source)
        elif isinstance(quote, (int, Source)):
            data["quote"] = quote
        elif isinstance(quote, MessageChain):
            data["quote"] = quote.getFirst(Source)
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
                val = await self.sendFriendMessage(**data)
            elif isinstance(data["target"], Group):
                val = await self.sendGroupMessage(**data)
            elif isinstance(data["target"], Member):
                val = await self.sendTempMessage(**data)
            else:
                logger.warning(
                    f"Unable to send {data['message']} to {data['target']} of type {type(data['target'])}"
                )
                return await action.result(BotMessage(messageId=-1, origin=data["message"]))
        except Exception as e:
            e.send_data = send_data  # type: ignore
            return await action.exception(cast(SendMessageException, e))
        else:
            return await action.result(val)

    @app_ctx_manager
    async def sendNudge(
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

    @app_ctx_manager
    async def recallMessage(self, target: Union[MessageChain, Source, BotMessage, int]) -> None:
        """撤回特定的消息; 撤回自己的消息需要在发出后 2 分钟内才能成功撤回; 如果在群组内, 需要撤回他人的消息则需要管理员/群主权限.

        Args:
            target (Union[Source, BotMessage, int]): 特定信息的 `messageId`, \
            可以是 `Source` 实例, `BotMessage` 实例或者是单纯的 int 整数.

        Returns:
            None: 没有返回.
        """

        if isinstance(target, BotMessage):
            target = target.messageId
        elif isinstance(target, Source):
            target = target.id
        elif isinstance(target, MessageChain):
            target = target.getFirst(Source).id
        await self.connection.call(
            "recall",
            CallMethod.POST,
            {
                "target": target,
            },
        )
