"""Ariadne 各种 model 存放的位置"""
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional, Union

from loguru import logger
from pydantic import BaseModel, Field, validator
from pydantic.main import BaseConfig, Extra
from pydantic.networks import AnyHttpUrl
from typing_extensions import Literal
from yarl import URL

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

    def default(self, o: Any) -> Any:
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
    log_level: str = "INFO"
    group_message_log_format: str = (
        "{bot_id}: [{group_name}({group_id})] {member_name}({member_id}) -> {message_string}"
    )
    friend_message_log_format: str = "{bot_id}: [{friend_name}({friend_id})] -> {message_string}"
    temp_message_log_format: str = (
        "{bot_id}: [{group_name}({group_id}).{member_name}({member_id})] -> {message_string}"
    )
    other_client_message_log_format: str = "{bot_id}: [{platform_name}({platform_id})] -> {message_string}"
    stranger_message_log_format: str = "{bot_id}: [{stranger_name}({stranger_id})] -> {message_string}"

    def initialize(self, app: "Ariadne"):
        """利用 Ariadne 对象注册事件日志处理器"""
        from .event.message import (
            FriendMessage,
            GroupMessage,
            OtherClientMessage,
            StrangerMessage,
            TempMessage,
        )

        @app.broadcast.receiver(GroupMessage)
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

        @app.broadcast.receiver(FriendMessage)
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

        @app.broadcast.receiver(TempMessage)
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

        @app.broadcast.receiver(StrangerMessage)
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

        @app.broadcast.receiver(OtherClientMessage)
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


class MiraiSession(AriadneBaseModel):
    """
    用于描述与上游接口会话, 并存储会话状态的实体类.

    Attributes:
        host (AnyHttpUrl): `mirai-api-http` 服务所在的根接口地址
        account (int): 应用所使用账号的整数 ID, 虽然启用 `singleMode` 时不需要, 但仍然建议填写.
        verify_key (str): 在 `mirai-api-http` 配置流程中定义, 需为相同的值以通过安全验证, 需在 mirai-api-http 配置里启用 `enableVerify`.
        session_key (str, optional): 会话标识, 即会话中用于进行操作的唯一认证凭证.
    """

    host: AnyHttpUrl
    single_mode: bool = False
    account: Optional[int] = None
    verify_key: Optional[str] = None
    session_key: Optional[str] = None
    version: Optional[str] = None

    def __init__(
        self,
        host: Union[AnyHttpUrl, str],
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


class Friend(AriadneBaseModel):
    """描述 Tencent QQ 中的好友."""

    id: int
    nickname: str
    remark: str


class Stranger(AriadneBaseModel):
    """描述 Tencent QQ 中的陌生人."""

    id: int
    nickname: str
    remark: str


class MemberPerm(Enum):
    """描述群成员在群组中所具备的权限"""

    Member = "MEMBER"  # 普通成员
    Administrator = "ADMINISTRATOR"  # 管理员
    Owner = "OWNER"  # 群主


class Group(AriadneBaseModel):
    """描述 Tencent QQ 中的群组."""

    id: int
    name: str
    accountPerm: MemberPerm = Field(..., alias="permission")


class Member(AriadneBaseModel):
    """描述用户在群组中所具备的有关状态, 包括所在群组, 群中昵称, 所具备的权限, 唯一ID."""

    id: int
    name: str = Field(..., alias="memberName")
    permission: MemberPerm
    specialTitle: Optional[str] = None
    joinTimestamp: Optional[int] = None
    lastSpeakTimestamp: Optional[int] = None
    mutetimeRemaining: Optional[int] = None
    group: Group


class GroupConfig(AriadneBaseModel):
    """描述群组各项功能的设置."""

    name: str = ""
    announcement: str = ""
    confessTalk: bool = False
    allowMemberInvite: bool = False
    autoApprove: bool = False
    anonymousChat: bool = False


class MemberInfo(AriadneBaseModel):
    """描述群组成员的可修改状态, 修改需要管理员/群主权限."""

    name: str = ""
    specialTitle: str = ""


class DownloadInfo(AriadneBaseModel):
    """描述一个文件的下载信息."""

    sha: str = ""
    md5: str = ""
    download_times: int = Field(..., alias="downloadTimes")
    uploader_id: int = Field(..., alias="uploaderId")
    upload_time: datetime = Field(..., alias="uploadTime")
    last_modify_time: datetime = Field(..., alias="lastModifyTime")
    url: Optional[str] = None


class FileInfo(AriadneBaseModel):
    """群组文件详细信息"""

    name: str = ""
    path: str = ""
    id: Optional[str] = ""
    parent: Optional["FileInfo"] = None
    contact: Optional[Union[Group, Friend]] = None
    is_file: bool = Field(..., alias="isFile")
    is_directory: bool = Field(..., alias="isDirectory")
    download_info: Optional[DownloadInfo] = Field(None, alias="downloadInfo")

    @validator("contact", pre=True, allow_reuse=True)
    def _(cls, val: Optional[dict]):
        if not val:
            return None
        if "remark" in val:  # Friend
            return Friend.parse_obj(val)
        return Group.parse_obj(val)  # Group


FileInfo.update_forward_refs(FileInfo=FileInfo)


class UploadMethod(Enum):
    """用于向 `upload` 系列方法描述上传类型"""

    Friend = "friend"
    Group = "group"
    Temp = "temp"


class CallMethod(Enum):
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
    platform: str


class Profile(AriadneBaseModel):
    """
    指示某个用户的个人资料
    """

    nickname: str
    email: Optional[str]
    age: Optional[int]
    level: int
    sign: str
    sex: Literal["UNKNOWN", "MALE", "FEMALE"]


class BotMessage(AriadneBaseModel):
    """
    指示 Bot 发出的消息.
    """

    messageId: int

    origin: Optional["MessageChain"]


class AriadneStatus(Enum):
    """指示 Ariadne 状态的枚举类"""

    STOP = "stop"
    LAUNCH = "launch"
    RUNNING = "running"
    SHUTDOWN = "shutdown"
    CLEANUP = "cleanup"
