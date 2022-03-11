"""Mirai 的各种事件"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from pydantic import Field
from typing_extensions import Literal

from ..exception import InvalidSession
from ..message.chain import MessageChain
from ..message.element import Element
from ..model import CallMethod, Client, Friend, Group, Member, MemberPerm
from ..typing import generic_issubclass
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
    """Bot 账号登录成功

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "BotOnlineEvent"
    qq: int


class BotOfflineEventActive(BotEvent):
    """Bot 账号主动离线

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "BotOfflineEventActive"
    qq: int


class BotOfflineEventForce(BotEvent):
    """Bot 账号被迫离线

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "BotOfflineEventForce"
    qq: int


class BotOfflineEventDropped(BotEvent):
    """Bot 账号与服务器的连接被服务器主动断开, 或因网络原因离线

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "BotOfflineEventDropped"
    qq: int


class BotReloginEvent(BotEvent):
    """Bot 账号正尝试重新登录

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "BotReloginEvent"
    qq: int


class FriendInputStatusChangedEvent(FriendEvent):
    """Bot 账号的某一好友输入状态改变.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "FriendInputStatusChangedEvent"
    friend: Friend
    inputting: bool

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, FriendInputStatusChangedEvent):
                if generic_issubclass(Friend, interface.annotation):
                    return interface.event.friend


class FriendNickChangedEvent(FriendEvent):
    """Bot 账号的某一好友更改了昵称.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Friend (annotation): 更改名称的好友
    """

    type = "FriendNickChangedEvent"
    friend: Friend
    from_name: str = Field(..., alias="from")
    to_name: str = Field(..., alias="to")

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, FriendNickChangedEvent):
                if generic_issubclass(Friend, interface.annotation):
                    return interface.event.friend


class BotGroupPermissionChangeEvent(GroupEvent, BotEvent):
    """Bot 账号在一特定群组内所具有的权限发生变化

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
    """

    type = "BotGroupPermissionChangeEvent"
    origin: MemberPerm
    current: MemberPerm
    group: Group

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, BotGroupPermissionChangeEvent):
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.group


class BotMuteEvent(GroupEvent, BotEvent):
    """Bot 账号在一特定群组内被管理员/群主禁言

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Member (annotation, optional = None): 执行禁言操作的管理员/群主, 若为 None 则为 Bot 账号操作
        Group (annotation): 发生该事件的群组
    """

    type = "BotMuteEvent"
    durationSeconds: int
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, BotMuteEvent):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.operator
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.operator.group


class BotUnmuteEvent(GroupEvent, BotEvent):
    """Bot 账号在一特定群组内被管理员/群主解除禁言

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Member (annotation, optional = None): 执行解除禁言操作的管理员/群主, 若为 None 则为 Bot 账号操作
        Group (annotation): 发生该事件的群组
    """

    type = "BotUnmuteEvent"
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, BotUnmuteEvent):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.operator
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.operator.group


class BotJoinGroupEvent(GroupEvent, BotEvent):
    """Bot 账号加入指定群组

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
        Member / Optional[Member] (annotation, optional = None): 邀请者, 可以为 None
    """

    type = "BotJoinGroupEvent"
    group: Group
    inviter: Optional[Member] = Field(..., alias="invitor")

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, BotJoinGroupEvent):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.inviter
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.group


class BotLeaveEventActive(GroupEvent, BotEvent):
    """Bot 账号主动退出了某群组.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
    """

    type: str = "BotLeaveEventActive"
    group: Group

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, BotLeaveEventActive):
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.group


class BotLeaveEventKick(GroupEvent, BotEvent):
    """Bot 账号被某群组的管理员/群主从该群组中删除.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
    """

    type: str = "BotLeaveEventKick"
    group: Group

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, BotLeaveEventKick):
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.group


class GroupRecallEvent(GroupEvent):
    """有群成员在指定群组撤回了一条消息, 注意, 这里的群成员若具有管理员/群主权限, 则他们可以撤回其他普通群员的消息, 且不受发出时间限制.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Member (annotation, optional): 执行本操作的群成员, 若为 None 则为 Bot 账号操作
        Group (annotation): 发生该事件的群组
    """

    type = "GroupRecallEvent"
    authorId: int
    messageId: int
    time: datetime
    group: Group
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, GroupRecallEvent):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.operator
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.group


class FriendRecallEvent(FriendEvent):
    """有一位与 Bot 账号为好友关系的用户撤回了一条消息

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "FriendRecallEvent"
    authorId: int
    messageId: int
    time: int
    operator: int


class NudgeEvent(MiraiEvent):
    """Bot 账号被某个账号在相应上下文区域进行 "戳一戳"(Nudge) 的行为.

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    提供的额外注解支持:
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
    """有一群组被修改了群名称

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 被修改了群名称的群组
        Member (annotation): 更改群名称的成员, 权限必定为管理员或是群主
    """

    type = "GroupNameChangeEvent"
    origin: str
    current: str
    group: Group
    operator: Optional[Member] = None

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, GroupNameChangeEvent):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.operator
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.group


class GroupEntranceAnnouncementChangeEvent(GroupEvent):
    """有一群组被修改了入群公告

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 被修改了入群公告的群组
        Member (annotation, optional = None): 作出此操作的管理员/群主, 若为 None 则为 Bot 账号操作
    """

    type = "GroupEntranceAnnouncementChangeEvent"
    origin: str
    current: str
    group: Group
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, GroupEntranceAnnouncementChangeEvent):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.operator
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.group


class GroupMuteAllEvent(GroupEvent):
    """有一群组开启了全体禁言

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 开启了全体禁言的群组
        Member (annotation, optional = None): 作出此操作的管理员/群主, 若为 None 则为 Bot 账号操作
    """

    type = "GroupMuteAllEvent"
    origin: bool
    current: bool
    group: Group
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, GroupMuteAllEvent):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.operator
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.group


class GroupAllowAnonymousChatEvent(GroupEvent):
    """有一群组修改了有关匿名聊天的相关设定

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 修改了相关设定的群组
        Member (annotation, optional = None): 作出此操作的管理员/群主, 若为 None 则为 Bot 账号操作
    """

    type = "GroupAllowAnonymousChatEvent"
    origin: bool
    current: bool
    group: Group
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, GroupAllowAnonymousChatEvent):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.operator
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.group


class GroupAllowConfessTalkEvent(GroupEvent):
    """有一群组修改了有关坦白说的相关设定

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 修改了相关设定的群组
        Member (annotation, optional = None): 作出此操作的管理员/群主, 若为 None 则为 Bot 账号操作
    """

    type = "GroupAllowConfessTalkEvent"
    origin: bool
    current: bool
    group: Group
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, GroupAllowConfessTalkEvent):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.operator
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.group


class GroupAllowMemberInviteEvent(GroupEvent):
    """有一群组修改了有关是否允许已有成员邀请其他用户加入群组的相关设定

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 修改了相关设定的群组
        Member (annotation, optional = None): 作出此操作的管理员/群主, 若为 None 则为 Bot 账号操作
    """

    type = "GroupAllowMemberInviteEvent"
    origin: bool
    current: bool
    group: Group
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, GroupAllowMemberInviteEvent):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.operator
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.group


class MemberJoinEvent(GroupEvent):
    """有一新成员加入了一特定群组

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 该用户加入的群组
        Member (annotation): 关于该用户的成员实例
    """

    type = "MemberJoinEvent"
    member: Member
    inviter: Optional[Member] = Field(..., alias="invitor")

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, MemberJoinEvent):
                if interface.name == "inviter" and generic_issubclass(Member, interface.annotation):
                    return interface.event.inviter
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.member
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.member.group


class MemberLeaveEventKick(GroupEvent):
    """有一群组成员被管理员/群主从群组中删除, 当 `operator` 为 `None` 时, 执行者为 Bot 账号.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 指定的群组
        Member (annotation):
          - `"target"` (default, const, str): 被从群组删除的成员
          - `"operator"` (default, const, str, optional = None): 执行了该操作的管理员/群主, 也可能是 Bot 账号.
    """

    type = "MemberLeaveEventKick"
    member: Member
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, MemberLeaveEventKick):
                if interface.name == "operator" and generic_issubclass(Member, interface.annotation):
                    return interface.event.operator
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.member
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.member.group


class MemberLeaveEventQuit(GroupEvent):
    """有一群组成员主动退出群组.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生本事件的群组, 通常的, 在本事件发生后本群组成员数量少于之前
        Member (annotation): 主动退出群组的成员
    """

    type = "MemberLeaveEventQuit"
    member: Member

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, MemberLeaveEventQuit):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.member
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.member.group


class MemberCardChangeEvent(GroupEvent):
    """有一群组成员的群名片被更改, 执行者可能是管理员/群主, 该成员自己, 也可能是 Bot 账号(这时, `operator` 为 `None`).

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
        Member (annotation):
          - `"target"` (default, const, str): 被更改群名片的成员
          - `"operator"` (default, const, Optional[str]): 该操作的执行者, 可能是管理员/群主, 该成员自己,
          也可能是 Bot 账号(这时, `operator` 为 `None`).
    """

    type = "MemberCardChangeEvent"
    origin: str
    current: str
    member: Member
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, MemberCardChangeEvent):
                if interface.name == "operator" and generic_issubclass(Member, interface.annotation):
                    return interface.event.operator
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.member
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.member.group


class MemberSpecialTitleChangeEvent(GroupEvent):
    """有一群组成员的群头衔被更改, 执行者只可能是群组的群主.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
        Member (annotation): 被更改群头衔的群组成员
    """

    type = "MemberSpecialTitleChangeEvent"
    origin: str
    current: str
    member: Member

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, MemberSpecialTitleChangeEvent):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.member
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.member.group


class MemberPermissionChangeEvent(GroupEvent):
    """有一群组成员的权限被更改/调整, 执行者只可能是群组的群主.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
        Member (annotation): 被调整权限的群组成员
    """

    type = "MemberPermissionChangeEvent"
    origin: str
    current: str
    member: Member

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, MemberPermissionChangeEvent):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.member
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.member.group


class MemberMuteEvent(GroupEvent):
    """有一群组成员被管理员/群组禁言, 当 `operator` 为 `None` 时为 Bot 账号操作.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
        Member (annotation):
          - `"target"` (default, const, str): 被禁言的成员
          - `"operator"` (default, const, str, optional = None): 该操作的执行者, 也可能是 Bot 账号.

          默认返回 `target`.
    """

    type = "MemberMuteEvent"
    durationSeconds: int
    member: Member
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, MemberMuteEvent):
                if interface.name == "operator" and generic_issubclass(Member, interface.annotation):
                    return interface.event.operator
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.member
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.member.group


class MemberUnmuteEvent(GroupEvent):
    """有一群组成员被管理员/群组解除禁言, 当 `operator` 为 `None` 时为 Bot 账号操作.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
        Member (annotation):
          - `"target"` (default, const, str): 被禁言的成员
          - `"operator"` (default, const, str, optional = None): 该操作的执行者, 可能是管理员或是群主, 也可能是 Bot 账号.

          默认返回 `target`.
    """

    type = "MemberUnmuteEvent"
    member: Member
    operator: Optional[Member]

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, MemberUnmuteEvent):
                if interface.name == "operator" and generic_issubclass(Member, interface.annotation):
                    return interface.event.operator
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.member
                if generic_issubclass(Group, interface.annotation):
                    return interface.event.member.group


class MemberHonorChangeEvent(GroupEvent):
    """有一群组成员获得/失去了某个荣誉.

    ** 注意: 当监听该事件或该类事件时, 请优先考虑使用原始事件类作为类型注解, 以此获得事件类实例, 便于获取更多的信息! **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
        Group (annotation): 发生该事件的群组
        Member (annotation): 获得/失去荣誉的成员
    """

    type = "MemberHonorChangeEvent"
    member: Member
    action: str
    honor: str

    class Dispatcher(BaseDispatcher):
        @staticmethod
        async def catch(interface: DispatcherInterface):
            if isinstance(interface.event, MemberHonorChangeEvent):
                if generic_issubclass(Member, interface.annotation):
                    return interface.event.member
                if generic_issubclass(Group, interface.annotation):
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
        from .. import get_running
        from ..adapter import Adapter

        adapter = get_running(Adapter)
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


class NewFriendRequestEvent(RequestEvent, FriendEvent):
    """有一用户向机器人提起好友请求.

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例

    事件拓展支持:
        该事件的处理需要你获取原始事件实例.

        1. 读取该事件的基础信息:

            ```python
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


class MemberJoinRequestEvent(RequestEvent, GroupEvent):
    """有一用户向机器人作为管理员/群主的群组申请加入群组.

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例

    事件拓展支持:
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


class BotInvitedJoinGroupRequestEvent(RequestEvent, BotEvent, GroupEvent):
    """Bot 账号接受到来自某个账号的邀请加入某个群组的请求.

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例

    事件拓展支持:
        该事件的处理需要你获取原始事件实例.

        1. 读取该事件的基础信息:

            ``` python
            event.supplicant: int # 邀请所辖账号加入群组的用户的 ID
            event.groupId: int # 对方邀请所辖账号加入的群组的 ID
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
    groupId: int = Field(..., alias="groupId")
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


class ClientKind(int, Enum):
    """详细设备类型。"""

    ANDROID_PAD = 68104
    AOL_CHAOJIHUIYUAN = 73730
    AOL_HUIYUAN = 73474
    AOL_SQQ = 69378
    CAR = 65806
    HRTX_IPHONE = 66566
    HRTX_PC = 66561
    MC_3G = 65795
    MISRO_MSG = 69634
    MOBILE_ANDROID = 65799
    MOBILE_ANDROID_NEW = 72450
    MOBILE_HD = 65805
    MOBILE_HD_NEW = 71426
    MOBILE_IPAD = 68361
    MOBILE_IPAD_NEW = 72194
    MOBILE_IPHONE = 67586
    MOBILE_OTHER = 65794
    MOBILE_PC_QQ = 65793
    MOBILE_PC_TIM = 77313
    MOBILE_WINPHONE_NEW = 72706
    QQ_FORELDER = 70922
    QQ_SERVICE = 71170
    TV_QQ = 69130
    WIN8 = 69899
    WINPHONE = 65804


class OtherClientOnlineEvent(MiraiEvent):
    """Bot 账号在其他客户端上线.

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "OtherClientOnlineEvent"
    client: Client
    kind: Optional[ClientKind]


class OtherClientOfflineEvent(MiraiEvent):
    """Bot 账号在其他客户端下线.

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "OtherClientOfflineEvent"
    client: Client


class CommandExecutedEvent(MiraiEvent):
    """有一条命令被执行

    ** 注意: 当监听该事件时, 请使用原始事件类作为类型注解, 以此获得事件类实例, 并执行相关操作. **

    - name (str): 命令名称
    - friend (Optional[Friend]): 发送命令的好友, 从控制台发送为 None
    - member (Optional[Member]): 发送命令的群成员, 从控制台发送为 None
    - args (List[Element]): 指令的参数, 以消息类型传递

    提供的额外注解支持:
        Ariadne (annotation): 发布事件的应用实例
    """

    type = "CommandExecutedEvent"
    name: str
    friend: Optional[Friend]
    member: Optional[Member]
    args: List[Element]

    def __init__(self, *args, **kwargs):
        if "args" in kwargs:
            kwargs["args"] = MessageChain.build_chain(kwargs["args"])
        super().__init__(*args, **kwargs)
