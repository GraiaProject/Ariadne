"""Ariadne 各种 model 存放的位置"""
import functools
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional, Union

from graia.broadcast.entities.listener import Listener
from loguru import logger
from pydantic import BaseModel, Field, validator
from pydantic.main import BaseConfig, Extra
from pydantic.networks import AnyHttpUrl
from typing_extensions import Literal
from yarl import URL

from graia.ariadne.util import gen_subclass

if TYPE_CHECKING:
    from .app import Ariadne
    from .message.chain import MessageChain
    from .typing import AbstractSetIntStr, DictStrAny, MappingIntStrAny


def datetime_encoder(v: datetime) -> float:
    """编码 datetime 对象

    Args:
        v (datetime): datetime 对象

    Returns:
        float: 编码后的 datetime (时间戳)
    """
    return v.timestamp()


class DatetimeEncoder(json.JSONEncoder):
    """可以编码 datetime 的 JSONEncoder"""

    def default(self, o):
        if isinstance(o, datetime):
            return int(o.timestamp())
        return super().default(o)


class AriadneBaseModel(BaseModel):
    """
    Ariadne 一切数据模型的基类.
    """

    def dict(
        self,
        *,
        include: Union["AbstractSetIntStr", "MappingIntStrAny"] = None,
        exclude: Union["AbstractSetIntStr", "MappingIntStrAny"] = None,
        by_alias: bool = False,
        skip_defaults: bool = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> "DictStrAny":
        _, _ = by_alias, exclude_none
        return super().dict(
            include=include,
            exclude=exclude,
            by_alias=True,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=True,
        )

    class Config(BaseConfig):
        """Ariadne BaseModel 设置"""

        extra = Extra.allow
        json_encoders = {
            datetime: datetime_encoder,
        }


@dataclass
class ChatLogConfig:
    """配置日志如何记录 QQ 消息与事件."""

    enabled: bool = True
    """是否开启聊天日志"""

    log_level: str = "INFO"
    """聊天日志的 log 等级"""

    group_message_log_format: str = (
        "{bot_id}: [{group_name}({group_id})] {member_name}({member_id}) -> {message_string}"
    )
    """群消息格式"""

    friend_message_log_format: str = "{bot_id}: [{friend_name}({friend_id})] -> {message_string}"
    """好友消息格式"""

    temp_message_log_format: str = (
        "{bot_id}: [{group_name}({group_id}).{member_name}({member_id})] -> {message_string}"
    )
    """临时消息格式"""

    other_client_message_log_format: str = "{bot_id}: [{platform_name}({platform_id})] -> {message_string}"
    """其他客户端消息格式"""

    stranger_message_log_format: str = "{bot_id}: [{stranger_name}({stranger_id})] -> {message_string}"
    """陌生人消息格式"""

    active_message_log_format: str = "{bot_id}: {sync_label}[{subject}] <- {message_string}"

    def initialize(self, app: "Ariadne"):
        """利用 Ariadne 对象注册事件日志处理器"""
        from .event.message import (
            ActiveMessage,
            FriendMessage,
            GroupMessage,
            OtherClientMessage,
            StrangerMessage,
            TempMessage,
        )

        @app.broadcast.receiver(GroupMessage, -1)
        def log_group_message(event: GroupMessage):
            logger.log(
                self.log_level,
                self.group_message_log_format.format(
                    group_id=event.sender.group.id,
                    group_name=event.sender.group.name,
                    member_id=event.sender.id,
                    member_name=event.sender.name,
                    member_permission=event.sender.permission.name,
                    bot_id=app.mirai_session.account,
                    message_string=event.messageChain.asDisplay().__repr__(),
                ),
            )

        @app.broadcast.receiver(FriendMessage, -1)
        def log_friend_message(event: FriendMessage):
            logger.log(
                self.log_level,
                self.friend_message_log_format.format(
                    bot_id=app.mirai_session.account,
                    friend_name=event.sender.nickname,
                    friend_id=event.sender.id,
                    message_string=event.messageChain.asDisplay().__repr__(),
                ),
            )

        @app.broadcast.receiver(TempMessage, -1)
        def log_temp_message(event: TempMessage):
            logger.log(
                self.log_level,
                self.temp_message_log_format.format(
                    group_id=event.sender.group.id,
                    group_name=event.sender.group.name,
                    member_id=event.sender.id,
                    member_name=event.sender.name,
                    member_permission=event.sender.permission.name,
                    bot_id=app.mirai_session.account,
                    message_string=event.messageChain.asDisplay().__repr__(),
                ),
            )

        @app.broadcast.receiver(StrangerMessage, -1)
        def log_stranger_message(event: StrangerMessage):
            logger.log(
                self.log_level,
                self.stranger_message_log_format.format(
                    bot_id=app.mirai_session.account,
                    stranger_name=event.sender.nickname,
                    stranger_id=event.sender.id,
                    message_string=event.messageChain.asDisplay().__repr__(),
                ),
            )

        @app.broadcast.receiver(OtherClientMessage, -1)
        def log_other_client_message(event: OtherClientMessage):
            logger.log(
                self.log_level,
                self.other_client_message_log_format.format(
                    bot_id=app.mirai_session.account,
                    platform_name=event.sender.platform,
                    platform_id=event.sender.id,
                    message_string=event.messageChain.asDisplay().__repr__(),
                ),
            )

        def log_active_message(event: ActiveMessage):
            logger.log(
                self.log_level,
                self.active_message_log_format.format(
                    bot_id=app.mirai_session.account,
                    sync_label="[SYNC]" if event.sync else "",
                    subject=event.subject,
                    message_string=event.messageChain.asDisplay().__repr__(),
                ),
            )

        app.broadcast.listeners.append(
            Listener(
                log_active_message,
                app.broadcast.getDefaultNamespace(),
                list(gen_subclass(ActiveMessage)),
                priority=-1,
            )
        )


class MiraiSession(AriadneBaseModel):
    """
    用于描述与上游接口会话, 并存储会话状态的实体类.

    Attributes:
        host (AnyHttpUrl): `mirai-api-http` 服务所在的根接口地址
        account (int): 应用所使用账号的整数 ID, 虽然启用 `singleMode` 时不需要, 但仍然建议填写.
        verify_key (str): 在 `mirai-api-http` 配置流程中定义, 需为相同的值以通过安全验证, 需在 mirai-api-http 配置里启用 `enableVerify`.
        session_key (str, optional): 会话标识, 即会话中用于进行操作的唯一认证凭证.
    """

    host: Optional[AnyHttpUrl]
    """链接地址, 以 http 开头, 作为服务器连接时应为 None"""

    single_mode: bool = False
    """mirai-console 是否开启 single_mode (单例模式)"""

    account: Optional[int] = None
    """账号"""

    verify_key: Optional[str] = None
    """mirai-api-http 配置的 VerifyKey 字段"""

    session_key: Optional[str] = None
    """会话标识"""

    version: Optional[str] = None
    """mirai-api-http 的版本"""

    def __init__(
        self,
        host: Optional[Union[AnyHttpUrl, str]] = None,
        account: Optional[Union[int, str]] = None,
        verify_key: Optional[str] = None,
        *,
        single_mode: bool = False,
    ) -> None:
        super().__init__(host=host, account=account, verify_key=verify_key, single_mode=single_mode)

    def url_gen(self, route: str) -> str:
        """生成 route 对应的 API URI

        Args:
            route (str): route 地址

        Returns:
            str: 对应的 API URI
        """
        return str(URL(self.host) / route)


@functools.total_ordering
class MemberPerm(Enum):
    """描述群成员在群组中所具备的权限"""

    Member = "MEMBER"  # 普通成员
    Administrator = "ADMINISTRATOR"  # 管理员
    Owner = "OWNER"  # 群主

    def __str__(self) -> str:
        return self.value

    def __lt__(self, other: "MemberPerm"):
        lv_map = {MemberPerm.Member: 1, MemberPerm.Administrator: 2, MemberPerm.Owner: 3}
        return lv_map[self] < lv_map[other]

    def __repr__(self) -> str:
        perm_map: Dict[str, str] = {
            "MEMBER": "<普通成员>",
            "ADMINISTRATOR": "<管理员>",
            "OWNER": "<群主>",
        }
        return perm_map[self.value]


class Group(AriadneBaseModel):
    """描述 Tencent QQ 中的群组."""

    id: int
    """群号"""

    name: str
    """群名"""

    accountPerm: MemberPerm = Field(..., alias="permission")
    """你在群中的权限"""

    def __int__(self):
        return self.id

    def __str__(self) -> str:
        return f"{self.name}({self.id})"

    async def getConfig(self) -> "GroupConfig":
        """获取该群组的 Config

        Returns:
            Config: 该群组的设置对象.
        """
        from . import get_running

        return await get_running().getGroupConfig(self)

    async def modifyConfig(self, config: "GroupConfig") -> None:
        """修改该群组的 Config

        Args:
            config (GroupConfig): 经过修改后的群设置对象.
        """
        from . import get_running

        return await get_running().modifyGroupConfig(self, config)

    async def getAvatar(self, cover: Optional[int] = None) -> bytes:
        """获取该群组的头像
        Args:
            cover (Optional[int]): 群封面标号 (若为 None 则获取该群头像, 否则获取该群封面)

        Returns:
            bytes: 群头像的二进制内容.
        """
        from . import get_running

        cover = (cover or 0) + 1
        return await (
            await get_running().adapter.session.get(f"https://p.qlogo.cn/gh/{self.id}/{self.id}_{cover}/")
        ).content.read()


class Member(AriadneBaseModel):
    """描述用户在群组中所具备的有关状态, 包括所在群组, 群中昵称, 所具备的权限, 唯一ID."""

    id: int
    """QQ 号"""

    name: str = Field(..., alias="memberName")
    """显示名称"""

    permission: MemberPerm
    """群权限"""

    specialTitle: Optional[str] = None
    """特殊头衔"""

    joinTimestamp: Optional[int] = None
    """加入的时间"""

    lastSpeakTimestamp: Optional[int] = None
    """最后发言时间"""

    mutetimeRemaining: Optional[int] = None
    """禁言剩余时间"""

    group: Group
    """所在群组"""

    def __str__(self) -> str:
        return f"{self.name}({self.id} @ {self.group})"

    def __int__(self):
        return self.id

    async def getProfile(self) -> "Profile":
        """获取该群成员的 Profile

        Returns:
            Profile: 该群成员的 Profile 对象
        """
        from . import get_running

        return await get_running().getMemberProfile(self)

    async def getInfo(self) -> "MemberInfo":
        """获取该成员的可修改状态

        Returns:
            MemberInfo: 群组成员的可修改状态
        """
        return MemberInfo(name=self.name, specialTitle=self.specialTitle)

    async def modifyInfo(self, info: "MemberInfo") -> None:
        """
        修改群组成员的可修改状态; 需要具有相应权限(管理员/群主).

        Args:
            info (MemberInfo): 已修改的指定群组成员的可修改状态

        Returns:
            None: 没有返回.
        """
        from . import get_running

        return await get_running().modifyMemberInfo(self, info)

    async def modifyAdmin(self, assign: bool) -> None:
        """
        修改一位群组成员管理员权限; 需要有相应权限(群主)

        Args:
            assign (bool): 是否设置群成员为管理员.

        Returns:
            None: 没有返回.
        """
        from . import get_running

        return await get_running().modifyMemberAdmin(assign, self)

    async def getAvatar(self, size: Literal[640, 140] = 640) -> bytes:
        """获取该群成员的头像

        Args:
            size (Literal[640, 140]): 头像尺寸

        Returns:
            bytes: 群成员头像的二进制内容.
        """
        from . import get_running

        return await (
            await get_running().adapter.session.get(f"https://q.qlogo.cn/g?b=qq&nk={self.id}&s={size}")
        ).content.read()


class Friend(AriadneBaseModel):
    """描述 Tencent QQ 中的好友."""

    id: int
    """QQ 号"""

    nickname: str
    """昵称"""

    remark: str
    """自行设置的代称"""

    def __int__(self):
        return self.id

    def __str__(self) -> str:
        return f"{self.remark}({self.id})"

    async def getProfile(self) -> "Profile":
        """获取该好友的 Profile

        Returns:
            Profile: 该好友的 Profile 对象
        """
        from . import get_running

        return await get_running().getFriendProfile(self)

    async def getAvatar(self, size: Literal[640, 140] = 640) -> bytes:
        """获取该好友的头像

        Args:
            size (Literal[640, 140]): 头像尺寸

        Returns:
            bytes: 好友头像的二进制内容.
        """
        from . import get_running

        return await (
            await get_running().adapter.session.get(f"https://q.qlogo.cn/g?b=qq&nk={self.id}&s={size}")
        ).content.read()


class Stranger(AriadneBaseModel):
    """描述 Tencent QQ 中的陌生人."""

    id: int
    """QQ 号"""

    nickname: str
    """昵称"""

    remark: str
    """自行设置的代称"""

    def __int__(self):
        return self.id

    def __str__(self) -> str:
        return f"Stranger({self.id}, {self.nickname})"

    async def getAvatar(self, size: Literal[640, 140] = 640) -> bytes:
        """获取该陌生人的头像

        Args:
            size (Literal[640, 140]): 头像尺寸

        Returns:
            bytes: 陌生人头像的二进制内容.
        """
        from . import get_running

        return await (
            await get_running().adapter.session.get(f"https://q.qlogo.cn/g?b=qq&nk={self.id}&s={size}")
        ).content.read()


class GroupConfig(AriadneBaseModel):
    """描述群组各项功能的设置."""

    name: str = ""
    """群名"""

    announcement: str = ""
    """群公告"""

    confessTalk: bool = False
    """开启坦白说"""

    allowMemberInvite: bool = False
    """允许群成员直接邀请入群"""

    autoApprove: bool = False
    """自动通过加群申请"""

    anonymousChat: bool = False
    """允许匿名聊天"""


class MemberInfo(AriadneBaseModel):
    """描述群组成员的可修改状态, 修改需要管理员/群主权限."""

    name: str = ""
    """昵称, 与 nickname不同"""

    specialTitle: str = ""
    """特殊头衔"""


class DownloadInfo(AriadneBaseModel):
    """描述一个文件的下载信息."""

    sha: str = ""
    """文件 SHA256"""

    md5: str = ""
    """文件 MD5"""

    download_times: int = Field(..., alias="downloadTimes")
    """下载次数"""

    uploader_id: int = Field(..., alias="uploaderId")
    """上传者 QQ 号"""

    upload_time: datetime = Field(..., alias="uploadTime")
    """上传时间"""

    last_modify_time: datetime = Field(..., alias="lastModifyTime")
    """最后修改时间"""

    url: Optional[str] = None
    """下载 url"""


class Announcement(AriadneBaseModel):
    """群公告"""

    group: Group
    """公告所在的群"""

    senderId: int
    """发送者QQ号"""

    fid: str
    """公告唯一标识ID"""

    allConfirmed: bool
    """群成员是否已全部确认"""

    confirmedMembersCount: int
    """已确认群成员人数"""

    publicationTime: datetime
    """公告发布时间"""


class FileInfo(AriadneBaseModel):
    """群组文件详细信息"""

    name: str = ""
    """文件名"""

    path: str = ""
    """文件路径的字符串表示"""

    id: Optional[str] = ""
    """文件 ID"""

    parent: Optional["FileInfo"] = None
    """父文件夹的 FileInfo 对象, 没有则表示存在于根目录"""

    contact: Optional[Union[Group, Friend]] = None
    """文件所在位置 (群组)"""

    is_file: bool = Field(..., alias="isFile")
    """是否为文件"""

    is_directory: bool = Field(..., alias="isDirectory")
    """是否为目录"""

    download_info: Optional[DownloadInfo] = Field(None, alias="downloadInfo")
    """下载信息"""

    @validator("contact", pre=True, allow_reuse=True)
    def _(cls, val: Optional[dict]):
        if not val:
            return None
        if "remark" in val:  # Friend
            return Friend.parse_obj(val)
        return Group.parse_obj(val)  # Group


FileInfo.update_forward_refs(FileInfo=FileInfo)


class UploadMethod(str, Enum):
    """用于向 `upload` 系列方法描述上传类型"""

    Friend = "friend"
    """好友"""

    Group = "group"
    """群组"""

    Temp = "temp"
    """临时消息"""

    def __str__(self) -> str:
        return self.value


class CallMethod(str, Enum):
    """
    用于向 `Adapter.call_api` 指示操作类型.
    """

    GET = "GET"
    POST = "POST"
    RESTGET = "get"
    RESTPOST = "update"
    MULTIPART = "multipart"


class Client(AriadneBaseModel):
    """
    指示其他客户端
    """

    id: int
    """客户端 ID"""

    platform: str
    """平台字符串表示"""


class Profile(AriadneBaseModel):
    """
    指示某个用户的个人资料
    """

    nickname: str
    """昵称"""

    email: Optional[str]
    """电子邮件地址"""

    age: Optional[int]
    """年龄"""

    level: int
    """QQ 等级"""

    sign: str
    """个性签名"""

    sex: Literal["UNKNOWN", "MALE", "FEMALE"]
    """性别"""


class BotMessage(AriadneBaseModel):
    """
    指示 Bot 发出的消息.
    """

    messageId: int
    """消息 ID"""

    origin: Optional["MessageChain"]
    """原始消息链 (发送的消息链)"""


class AriadneStatus(Enum):
    """指示 Ariadne 状态的枚举类"""

    STOP = "stop"
    """已停止"""

    LAUNCH = "launch"
    """正在启动"""

    RUNNING = "running"
    """正常运行"""

    SHUTDOWN = "shutdown"
    """刚开始关闭"""

    CLEANUP = "cleanup"
    """清理残留任务"""
