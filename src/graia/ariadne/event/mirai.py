"""Mirai 的各种事件"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from pydantic import Field
from typing_extensions import Literal

from ..context import adapter_ctx
from ..dispatcher import ContextDispatcher
from ..exception import InvalidSession
from ..message.element import Element
from ..model import CallMethod, Client, Friend, Group, Member, MemberPerm
from . import MiraiEvent


class BotEvent(MiraiEvent):
    """
    指示有关 Bot 本身的事件.
    """


class FriendEvent(MiraiEvent):
    """
    指示有关好友的事件.
    """


class GroupEvent(MiraiEvent):
    """
    指示有关群组的事件.
    """


class BotOnlineEvent(BotEvent):
    """当该事件发生时, 应用实例所辖账号登录成功

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "BotOnlineEvent"
    qq: int


class BotOfflineEventActive(BotEvent):
    """当该事件发生时, 应用实例所辖账号主动离线

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "BotOfflineEventActive"
    qq: int


class BotOfflineEventForce(BotEvent):
    """当该事件发生时, 应用实例所辖账号被迫离线

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "BotOfflineEventForce"
    qq: int


class BotOfflineEventDropped(BotEvent):
    """当该事件发生时, 应用实例所辖账号与服务器的连接被服务器主动断开, 或因网络原因离线

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "BotOfflineEventDropped"
    qq: int


class BotReloginEvent(BotEvent):
    """当该事件发生时, 应用实例所辖账号正尝试重新登录

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "BotReloginEvent"
    qq: int


class FriendInputStatusChangedEvent(FriendEvent):
    """当该事件发生时, 应用实例所辖账号的某一好友输入状态改变.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "FriendInputStatusChangedEvent"
    friend: Friend
    inputting: bool


class FriendNickChangedEvent(FriendEvent):
    """当该事件发生时, 应用实例所辖账号的某一好友更改了昵称.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "FriendNickChangedEvent"
    friend: Friend
    from_name: str = Field(..., alias="from")
    to_name: str = Field(..., alias="to")


class BotGroupPermissionChangeEvent(GroupEvent, BotEvent):
    """当该事件发生时, 应用实例所辖账号在一特定群组内所具有的权限发生变化

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "BotGroupPermissionChangeEvent"
    origin: MemberPerm
    current: MemberPerm
    group: Group


class BotMuteEvent(GroupEvent, BotEvent):
    """当该事件发生时, 应用实例所辖账号在一特定群组内被管理员/群主禁言

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Member (annotation, optional = None): 执行禁言操作的管理员/群主, 若为 None 则为应用实例所辖账号操作
        Group (annotation, optional = None): 发生该事件的群组
    """

    type = "BotMuteEvent"
    durationSeconds: int
    operator: Optional[Member]
    group: Optional[Group]

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["BotMuteEvent"]):
            if interface.annotation is Member:
                return interface.event.operator
            if interface.annotation is Group:
                return interface.event.group


class BotUnmuteEvent(GroupEvent, BotEvent):
    """当该事件发生时, 应用实例所辖账号在一特定群组内被管理员/群主解除禁言

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Member (annotation, optional = None): 执行解除禁言操作的管理员/群主, 若为 None 则为应用实例所辖账号操作
        Group (annotation, optional = None): 发生该事件的群组
    """

    type = "BotUnmuteEvent"
    operator: Optional[Member]
    group: Optional[Group]

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["BotUnmuteEvent"]):
            if interface.annotation is Member:
                return interface.event.operator
            if interface.annotation is Group:
                return interface.event.group


class BotJoinGroupEvent(GroupEvent, BotEvent):
    """当该事件发生时, 应用实例所辖账号加入指定群组

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation, optional = None): 发生该事件的群组
    """

    type = "BotJoinGroupEvent"
    group: Group
    inviter: Optional[Member] = Field(..., alias="invitor")  # F**k you typo

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["BotJoinGroupEvent"]):
            if interface.annotation is Group:
                return interface.event.group


class BotLeaveEventActive(GroupEvent, BotEvent):
    """当该事件发生时, 应用实例所辖账号主动退出了某群组.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation, optional = None): 发生该事件的群组
    """

    type: str = "BotLeaveEventActive"
    group: Group

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["BotLeaveEventActive"]):
            if interface.annotation is Group:
                return interface.event.group


class BotLeaveEventKick(GroupEvent, BotEvent):
    """当该事件发生时, 应用实例所辖账号被某群组的管理员/群主从该群组中删除.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation, optional = None): 发生该事件的群组
    """

    type: str = "BotLeaveEventKick"
    group: Group

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["BotLeaveEventKick"]):
            if interface.annotation is Group:
                return interface.event.group


class GroupRecallEvent(GroupEvent):
    """当该事件发生时, 有群成员在指定群组撤回了一条消息, 注意, 这里的群成员若具有管理员/群主权限, 则他们可以撤回其他普通群员的消息, 且不受发出时间限制.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Member (annotation, return:optional): 执行本操作的群成员, 若为 None 则为应用实例所辖账号操作
        Group (annotation): 发生该事件的群组
    """

    type = "GroupRecallEvent"
    authorId: int
    messageId: int
    time: datetime
    group: Group
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["GroupRecallEvent"]):
            if interface.annotation is Group:
                return interface.event.group
            if interface.annotation is Member:
                return interface.event.operator


class FriendRecallEvent(FriendEvent):
    """当该事件发生时, 有一位与应用实例所辖账号为好友关系的用户撤回了一条消息

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "FriendRecallEvent"
    authorId: int
    messageId: int
    time: int
    operator: int


class NudgeEvent(MiraiEvent):
    """当该事件发生时, 应用实例所辖账号被某个账号在相应上下文区域进行 "戳一戳"(Nudge) 的行为.

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
    """

    type: str = "NudgeEvent"
    supplicant: int = Field(..., alias="fromId")  # 即请求方 QQ
    target: int

    msg_action: str = Field(..., alias="action")
    msg_suffix: str = Field(..., alias="suffix")
    origin_subject_info: Dict[str, Any] = Field(..., alias="subject")

    friend_id: Optional[int] = None
    group_id: Optional[int] = None

    context_type: Literal["friend", "group", "stranger", None] = None

    def __init__(self, **data: Any) -> None:
        ctx_type = data["context_type"] = str.lower(data["subject"]["kind"])
        if ctx_type == "group":
            data["group_id"] = data["subject"]["id"]
        else:
            data["friend_id"] = data["subject"]["id"]
        super().__init__(**data)


class GroupNameChangeEvent(GroupEvent):
    """该事件发生时, 有一群组被修改了群名称

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 被修改了群名称的群组
        Member (annotation): 更改群名称的成员, 权限必定为管理员或是群主
    """

    type = "GroupNameChangeEvent"
    origin: str
    current: str
    group: Group
    operator: Optional[Member] = None

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["GroupNameChangeEvent"]):
            if interface.annotation is Group:
                return interface.event.group
            if interface.annotation is Member:
                return interface.event.operator


class GroupEntranceAnnouncementChangeEvent(GroupEvent):
    """该事件发生时, 有一群组被修改了入群公告

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 被修改了入群公告的群组
        Member (annotation, return:optional): 作出此操作的管理员/群主, 若为 None 则为应用实例所辖账号操作
    """

    type = "GroupEntranceAnnouncementChangeEvent"
    origin: str
    current: str
    group: Group
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(
            interface: DispatcherInterface["GroupEntranceAnnouncementChangeEvent"],
        ):
            if interface.annotation is Group:
                return interface.event.group
            if interface.annotation is Member:
                return interface.event.operator


class GroupMuteAllEvent(GroupEvent):
    """该事件发生时, 有一群组开启了全体禁言

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 开启了全体禁言的群组
        Member (annotation, return:optional): 作出此操作的管理员/群主, 若为 None 则为应用实例所辖账号操作
    """

    type = "GroupMuteAllEvent"
    origin: bool
    current: bool
    group: Group
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["GroupMuteAllEvent"]):
            if interface.annotation is Group:
                return interface.event.group
            if interface.annotation is Member:
                return interface.event.operator


class GroupAllowAnonymousChatEvent(GroupEvent):
    """该事件发生时, 有一群组修改了有关匿名聊天的相关设定

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 修改了相关设定的群组
        Member (annotation, return:optional): 作出此操作的管理员/群主, 若为 None 则为应用实例所辖账号操作
    """

    type = "GroupAllowAnonymousChatEvent"
    origin: bool
    current: bool
    group: Group
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["GroupAllowAnonymousChatEvent"]):
            if interface.annotation is Group:
                return interface.event.group
            if interface.annotation is Member:
                return interface.event.operator


class GroupAllowConfessTalkEvent(GroupEvent):
    """该事件发生时, 有一群组修改了有关坦白说的相关设定

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 修改了相关设定的群组
        Member (annotation, return:optional): 作出此操作的管理员/群主, 若为 None 则为应用实例所辖账号操作
    """

    type = "GroupAllowConfessTalkEvent"
    origin: bool
    current: bool
    group: Group
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["GroupAllowConfessTalkEvent"]):
            if interface.annotation is Group:
                return interface.event.group
            if interface.annotation is Member:
                return interface.event.operator


class GroupAllowMemberInviteEvent(GroupEvent):
    """该事件发生时, 有一群组修改了有关是否允许已有成员邀请其他用户加入群组的相关设定

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 修改了相关设定的群组
        Member (annotation, return:optional): 作出此操作的管理员/群主, 若为 None 则为应用实例所辖账号操作
    """

    type = "GroupAllowMemberInviteEvent"
    origin: bool
    current: bool
    group: Group
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["GroupAllowMemberInviteEvent"]):
            if interface.annotation is Group:
                return interface.event.group
            if interface.annotation is Member:
                return interface.event.operator


class MemberJoinEvent(GroupEvent):
    """该事件发生时, 有一新成员加入了一特定群组

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 该用户加入的群组
        Member (annotation): 关于该用户的成员实例
    """

    type = "MemberJoinEvent"
    member: Member
    inviter: Optional[Member] = Field(..., alias="invitor")

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["MemberJoinEvent"]):
            if interface.annotation is Member:
                return interface.event.member
            if interface.annotation is Group:
                return interface.event.member.group


class MemberLeaveEventKick(GroupEvent):
    """该事件发生时, 有一群组成员被管理员/群主从群组中删除, 当 `operator` 为 `None` 时, 执行者为应用实例所辖账号.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 指定的群组
        Member (annotation):
          - `"target"` (default, const, str): 被从群组删除的成员
          - `"operator"` (default, const, str, return:optional): 执行了该操作的管理员/群主, 也可能是应用实例所辖账号.
    """

    type = "MemberLeaveEventKick"
    member: Member
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["MemberLeaveEventKick"]):
            if interface.annotation is Member:
                if interface.name == "target":
                    return interface.event.member
                if interface.name == "operator":
                    return interface.event.operator
            elif interface.annotation is Group:
                return interface.event.member.group


class MemberLeaveEventQuit(GroupEvent):
    """该事件发生时, 有一群组成员主动退出群组.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生本事件的群组, 通常的, 在本事件发生后本群组成员数量少于之前
        Member (annotation): 主动退出群组的成员
    """

    type = "MemberLeaveEventQuit"
    member: Member

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["MemberLeaveEventQuit"]):
            if interface.annotation is Member:
                return interface.event.member
            if interface.annotation is Group:
                return interface.event.member.group


class MemberCardChangeEvent(GroupEvent):
    """该事件发生时, 有一群组成员的群名片被更改, 执行者可能是管理员/群主, 该成员自己, 也可能是应用实例所辖账号(这时, `operator` 为 `None`).

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
        Member (annotation):
          - `"target"` (default, const, str): 被更改群名片的成员
          - `"operator"` (default, const, Optional[str]): 该操作的执行者, 可能是管理员/群主, 该成员自己,
          也可能是应用实例所辖账号(这时, `operator` 为 `None`).
    """

    type = "MemberCardChangeEvent"
    origin: str
    current: str
    member: Member
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["MemberCardChangeEvent"]):
            if interface.annotation is Member:
                if interface.name == "target":
                    return interface.event.member
                if interface.name == "operator":
                    return interface.event.operator
            elif interface.annotation is Group:
                return interface.event.member.group


class MemberSpecialTitleChangeEvent(GroupEvent):
    """该事件发生时, 有一群组成员的群头衔被更改, 执行者只可能是群组的群主.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
        Member (annotation): 被更改群头衔的群组成员
    """

    type = "MemberSpecialTitleChangeEvent"
    origin: str
    current: str
    member: Member

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(
            interface: DispatcherInterface["MemberSpecialTitleChangeEvent"],
        ):
            if interface.annotation is Member:
                return interface.event.member
            if interface.annotation is Group:
                return interface.event.member.group


class MemberPermissionChangeEvent(GroupEvent):
    """该事件发生时, 有一群组成员的权限被更改/调整, 执行者只可能是群组的群主.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
        Member (annotation): 被调整权限的群组成员
    """

    type = "MemberPermissionChangeEvent"
    origin: str
    current: str
    member: Member

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["MemberPermissionChangeEvent"]):
            if interface.annotation is Member:
                return interface.event.member
            if interface.annotation is Group:
                return interface.event.member.group


class MemberMuteEvent(MiraiEvent):
    """该事件发生时, 有一群组成员被管理员/群组禁言, 当 `operator` 为 `None` 时为应用实例所辖账号操作.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
        Member (annotation):
          - `"target"` (default, const, str): 被禁言的成员
          - `"operator"` (default, const, str, return:optional): 该操作的执行者, 也可能是应用实例所辖账号.
    """

    type = "MemberMuteEvent"
    durationSeconds: int
    member: Member
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["MemberMuteEvent"]):
            if interface.annotation is Member:
                if interface.name == "target":
                    return interface.event.member
                if interface.name == "operator":
                    return interface.event.operator
            elif interface.annotation is Group:
                return interface.event.member.group


class MemberUnmuteEvent(GroupEvent):
    """该事件发生时, 有一群组成员被管理员/群组解除禁言, 当 `operator` 为 `None` 时为应用实例所辖账号操作.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
        Member (annotation):
          - `"target"` (default, const, str): 被禁言的成员
          - `"operator"` (default, const, str, return:optional): 该操作的执行者, 可能是管理员或是群主, 也可能是应用实例所辖账号.
    """

    type = "MemberUnmuteEvent"
    member: Member
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["MemberUnmuteEvent"]):
            if interface.annotation is Member:
                if interface.name == "target":
                    return interface.event.member
                if interface.name == "operator":
                    return interface.event.operator
            elif interface.annotation is Group:
                return interface.event.member.group


class MemberHonorChangeEvent(GroupEvent):
    """该事件发生时, 有一群组成员获得/失去了某个荣誉.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
        Member (annotation): 获得/失去荣誉的成员
    """

    type = "MemberHonorChangeEvent"
    member: Member
    action: str
    honor: str

    class Dispatcher(BaseDispatcher):  # pylint: disable=missing-class-docstring
        mixin = [ContextDispatcher]

        @staticmethod
        async def catch(interface: DispatcherInterface["MemberHonorChangeEvent"]):
            if interface.annotation is Member:
                return interface.event.member
            if interface.annotation is Group:
                return interface.event.member.group


class RequestEvent(MiraiEvent):
    """
    各种申请事件的基类.
    """

    type: str
    requestId: int = Field(..., alias="eventId")
    supplicant: int = Field(..., alias="fromId")  # 即请求方 QQ
    sourceGroup: Optional[int] = Field(..., alias="groupId")
    nickname: str = Field(..., alias="nick")
    message: str

    async def _operate(self, operation: int, msg: str = "") -> None:
        """
        内部接口, 用于内部便捷发送相应操作.
        """
        adapter = adapter_ctx.get()
        if not adapter.mirai_session.session_key:
            raise InvalidSession("you must authenticate before this.")
        api_route = self.type[0].lower() + self.type[1:]
        await adapter.call_api(
            f"resp/{api_route}",
            CallMethod.POST,
            {
                "sessionKey": adapter.mirai_session.session_key,
                "eventId": self.requestId,
                "fromId": self.supplicant,
                "groupId": self.sourceGroup,
                "operate": operation,
                "message": msg,
            },
        )


class NewFriendRequestEvent(RequestEvent):
    """当该事件发生时, 有一用户向机器人提起好友请求.

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例

    Addon Introduction:
        该事件的处理需要你获取原始事件实例.
        1. 读取该事件的基础信息:
        ``` python
        event.supplicant: int # 发起加好友请求的用户的 ID
        event.sourceGroup: Optional[int] # 对方可能是从某个群发起对账号的请求的, mirai 可以解析对方从哪个群发起的请求.
        event.nickname: str # 对方的昵称
        event.message: str # 对方发起请求时填写的描述
        ```

        2. 同意请求: `await event.accept()`, 具体查看该方法所附带的说明.
        3. 拒绝请求: `await event.reject()`, 具体查看该方法所附带的说明.
        4. 拒绝并不再接受来自对方的请求: `await event.rejectAndBlock()`, 具体查看该方法所附带的说明.
    """

    type = "NewFriendRequestEvent"

    async def accept(self, message: str = "") -> None:
        """同意对方的加好友请求.

        Args:
            message (str, optional): 附带给对方的消息. 默认为 "".

        Raises:
            LookupError: 尝试上下文外处理事件.
            InvalidSession: 应用实例没准备好!

        Returns:
            None: 没有返回.
        """
        await self._operate(0, message)

    async def reject(self, message: str = "") -> None:
        """拒绝对方的加好友请求.

        Args:
            message (str, optional): 附带给对方的消息. 默认为 "".

        Raises:
            LookupError: 尝试上下文外处理事件.
            InvalidSession: 应用实例没准备好!

        Returns:
            None: 没有返回.
        """
        await self._operate(1, message)

    async def rejectAndBlock(self, message: str = "") -> None:
        """拒绝对方的加好友请求, 并不再接受来自对方的加好友请求.

        Args:
            message (str, optional): 附带给对方的消息. 默认为 "".

        Raises:
            LookupError: 尝试上下文外处理事件.
            InvalidSession: 应用实例没准备好!

        Returns:
            None: 没有返回.
        """
        await self._operate(2, message)


class MemberJoinRequestEvent(RequestEvent):
    """当该事件发生时, 有一用户向机器人作为管理员/群主的群组申请加入群组.

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例

    Addon Introduction:
        该事件的处理需要你获取原始事件实例.
        1. 读取该事件的基础信息:
        ``` python
        event.supplicant: int # 申请加入群组的用户的 ID
        event.groupId: Optional[int] # 对方试图加入的群组的 ID
        event.groupName: str # 对方试图加入的群组的名称
        event.nickname: str # 对方的昵称
        event.message: str # 对方发起请求时填写的描述
        ```

        2. 同意请求: `await event.accept()`, 具体查看该方法所附带的说明.
        3. 拒绝请求: `await event.reject()`, 具体查看该方法所附带的说明.
        4. 忽略请求: `await event.ignore()`, 具体查看该方法所附带的说明.
        5. 拒绝并不再接受来自对方的请求: `await event.rejectAndBlock()`, 具体查看该方法所附带的说明.
        6. 忽略并不再接受来自对方的请求: `await event.ignoreAndBlock()`, 具体查看该方法所附带的说明.
    """

    type = "MemberJoinRequestEvent"
    requestId: int = Field(..., alias="eventId")
    supplicant: int = Field(..., alias="fromId")  # 即请求方 QQ
    groupId: Optional[int] = Field(..., alias="groupId")
    groupName: str = Field(..., alias="groupName")
    nickname: str = Field(..., alias="nick")
    message: str

    async def accept(self, message: str = "") -> None:
        """同意对方加入群组.

        Args:
            message (str, optional): 附带给对方的消息. 默认为 "".

        Raises:
            LookupError: 尝试上下文外处理事件.
            InvalidSession: 应用实例没准备好!

        Returns:
            None: 没有返回.
        """
        await self._operate(0, message)

    async def reject(self, message: str = "") -> None:
        """拒绝对方加入群组.

        Args:
            message (str, optional): 附带给对方的消息. 默认为 "".

        Raises:
            LookupError: 尝试上下文外处理事件.
            InvalidSession: 应用实例没准备好!

        Returns:
            None: 没有返回.
        """
        await self._operate(1, message)

    async def ignore(self, message: str = "") -> None:
        """忽略对方加入群组的请求.

        Args:
            message (str, optional): 附带给对方的消息. 默认为 "".

        Raises:
            LookupError: 尝试上下文外处理事件.
            InvalidSession: 应用实例没准备好!

        Returns:
            None: 没有返回.
        """
        await self._operate(2, message)

    async def rejectAndBlock(self, message: str = "") -> None:
        """拒绝对方加入群组的请求, 并不再接受来自对方加入群组的请求.

        Args:
            message (str, optional): 附带给对方的消息. 默认为 "".

        Raises:
            LookupError: 尝试上下文外处理事件.
            InvalidSession: 应用实例没准备好!

        Returns:
            None: 没有返回.
        """
        await self._operate(3, message)

    async def ignoreAndBlock(self, message: str = "") -> None:
        """忽略对方加入群组的请求, 并不再接受来自对方加入群组的请求.

        Args:
            message (str, optional): 附带给对方的消息. 默认为 "".

        Raises:
            LookupError: 尝试上下文外处理事件.
            InvalidSession: 应用实例没准备好!

        Returns:
            None: 没有返回.
        """
        await self._operate(4, message)


class BotInvitedJoinGroupRequestEvent(RequestEvent):
    """当该事件发生时, 应用实例所辖账号接受到来自某个账号的邀请加入某个群组的请求.

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例

    Addon Introduction:
        该事件的处理需要你获取原始事件实例.
        1. 读取该事件的基础信息:
        ``` python
        event.supplicant: int # 邀请所辖账号加入群组的用户的 ID
        event.groupId: Optional[int] # 对方邀请所辖账号加入的群组的 ID
        event.groupName: str # 对方邀请所辖账号加入的群组的名称
        event.nickname: str # 对方的昵称
        event.message: str # 对方发起请求时填写的描述
        ```

        2. 同意请求: `await event.accept()`, 具体查看该方法所附带的说明.
        3. 拒绝请求: `await event.reject()`, 具体查看该方法所附带的说明.
    """

    type = "BotInvitedJoinGroupRequestEvent"
    requestId: int = Field(..., alias="eventId")
    supplicant: int = Field(..., alias="fromId")  # 即请求方 QQ
    groupId: Optional[int] = Field(..., alias="groupId")
    groupName: str = Field(..., alias="groupName")
    nickname: str = Field(..., alias="nick")
    message: str

    async def accept(self, message: str = "") -> None:
        """接受邀请并加入群组/发起对指定群组的加入申请.

        Args:
            message (str, optional): 附带给对方的消息. 默认为 "".

        Raises:
            LookupError: 尝试上下文外处理事件.
            InvalidSession: 应用实例没准备好!

        Returns:
            None: 没有返回.
        """
        await self._operate(0, message)

    async def reject(self, message: str = "") -> None:
        """拒绝对方加入指定群组的邀请.

        Args:
            message (str, optional): 附带给对方的消息. 默认为 "".

        Raises:
            LookupError: 尝试上下文外处理事件.
            InvalidSession: 应用实例没准备好!

        Returns:
            None: 没有返回.
        """
        await self._operate(1, message)


class OtherClientOnlineEvent(MiraiEvent):
    """当该事件发生时, 应用实例所辖账号在其他客户端上线.

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "OtherClientOnlineEvent"
    client: Client
    kind: Optional[int]


class OtherClientOfflineEvent(MiraiEvent):
    """当该事件发生时, 应用实例所辖账号在其他客户端下线.

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "OtherClientOfflineEvent"
    client: Client


class CommandExecutedEvent(MiraiEvent):
    """当该事件发生时, 有一条命令被执行

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    Allowed Extra Parameters(提供的额外注解支持):
        Ariadne (annotation): 发布事件的应用实例
    """

    eventId: int
    name: str
    friend: Optional[Friend]
    member: Optional[Member]
    args: List[Element]
