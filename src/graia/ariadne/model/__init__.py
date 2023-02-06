"""Ariadne 各种 model 存放的位置"""
import functools
from datetime import datetime
from typing import TYPE_CHECKING, Awaitable, Callable, Dict, Literal, Optional, Type, Union

from loguru import logger
from pydantic import Field, validator

from ..util import gen_subclass, internal_cls

if TYPE_CHECKING:
    from ..app import Ariadne
    from ..event import MiraiEvent

from .relationship import Client as Client
from .relationship import Friend as Friend
from .relationship import Group as Group
from .relationship import GroupConfig as GroupConfig
from .relationship import Member as Member
from .relationship import MemberInfo as MemberInfo
from .relationship import MemberPerm as MemberPerm
from .relationship import Stranger as Stranger
from .util import AriadneBaseModel as AriadneBaseModel


class LogConfig(Dict[Type["MiraiEvent"], Optional[str]]):
    def __init__(
        self,
        log_level: Union[str, Callable[["MiraiEvent"], Optional[str]]] = "INFO",
        extra: Optional[Dict[Union[Type["MiraiEvent"], str], Optional[str]]] = None,
    ):
        """
        Args:
            log_level (Union[str, Callable[["MiraiEvent"], str]]): 日志级别, \
            可以是字符串或者一个函数, 函数的参数是 MiraiEvent 对象, 返回字符串
            extra (Optional[Dict[Type["MiraiEvent"], str], Optional[str]]]): \
            额外的事件日志格式, 键为事件类型或事件名, 值为日志格式, None 则禁用该事件日志
        """
        from ..event import MiraiEvent
        from ..event.message import (
            ActiveMessage,
            FriendMessage,
            GroupMessage,
            OtherClientMessage,
            StrangerMessage,
            TempMessage,
        )

        extra = extra or {}

        self.log_level: Callable[[MiraiEvent], Optional[str]] = (
            log_level if callable(log_level) else lambda _: log_level
        )

        account_seg = "{ariadne.account}"
        msg_chain_seg = "{event.message_chain.safe_display}"
        sender_seg = "{event.sender.name}({event.sender.id})"
        user_seg = "{event.sender.nickname}({event.sender.id})"
        group_seg = "{event.sender.group.name}({event.sender.group.id})"
        client_seg = "{event.sender.platform}({event.sender.id})"
        self.update(
            {
                GroupMessage: f"{account_seg}: [RECV][{group_seg}] {sender_seg} -> {msg_chain_seg}",
                TempMessage: f"{account_seg}: [RECV][{group_seg}:{sender_seg}] -> {msg_chain_seg}",
                FriendMessage: f"{account_seg}: [RECV][{user_seg}] -> {msg_chain_seg}",
                StrangerMessage: f"{account_seg}: [RECV][{user_seg}] -> {msg_chain_seg}",
                OtherClientMessage: f"{account_seg}: [RECV][{client_seg}] -> {msg_chain_seg}",
            }
        )
        for active_msg_cls in gen_subclass(ActiveMessage):
            label: str = "[SYNC] " if active_msg_cls.__fields__["sync"].default else "[SEND]"
            self[active_msg_cls] = f"{account_seg}: {label}[{{event.subject}}] <- {msg_chain_seg}"
        self.update({sub: extra[sub.__name__] for sub in gen_subclass(MiraiEvent) if sub.__name__ in extra})

    def event_hook(self, app: "Ariadne") -> Callable[["MiraiEvent"], Awaitable[None]]:
        return functools.partial(self.log, app)

    async def log(self, app: "Ariadne", event: "MiraiEvent") -> None:
        log_level: Optional[str] = self.log_level(event)
        fmt: Optional[str] = self.get(type(event))
        if log_level and fmt:
            logger.log(log_level, fmt.format(event=event, ariadne=app))


@internal_cls()
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


@internal_cls()
class Announcement(AriadneBaseModel):
    """群公告"""

    group: Group
    """公告所在的群"""

    senderId: int
    """发送者QQ号"""

    fid: str
    """公告唯一标识ID"""

    all_confirmed: bool = Field(..., alias="allConfirmed")
    """群成员是否已全部确认"""

    confirmed_members_count: int = Field(..., alias="confirmedMembersCount")
    """已确认群成员人数"""

    publication_time: datetime = Field(..., alias="publicationTime")
    """公告发布时间"""


@internal_cls()
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
        return Friend.parse_obj(val) if "remark" in val else Group.parse_obj(val)


FileInfo.update_forward_refs(FileInfo=FileInfo)


@internal_cls()
class Profile(AriadneBaseModel):
    """指示某个用户的个人资料"""

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


__all__ = [
    "Client",
    "Friend",
    "Group",
    "GroupConfig",
    "Member",
    "MemberInfo",
    "MemberPerm",
    "Stranger",
    "AriadneBaseModel",
    "LogConfig",
    "DownloadInfo",
    "Announcement",
    "FileInfo",
    "Profile",
]
