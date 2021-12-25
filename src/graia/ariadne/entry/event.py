"""Ariadne 事件相关的导入集合"""

# no error

from graia.ariadne.event import MiraiEvent
from graia.ariadne.event.lifecycle import (
    AdapterLaunched,
    AdapterShutdowned,
    ApplicationLaunched,
    ApplicationLifecycleEvent,
    ApplicationShutdowned,
)
from graia.ariadne.event.message import (
    FriendMessage,
    GroupMessage,
    OtherClientMessage,
    StrangerMessage,
    TempMessage,
)
from graia.ariadne.event.mirai import (
    BotEvent,
    BotGroupPermissionChangeEvent,
    BotInvitedJoinGroupRequestEvent,
    BotJoinGroupEvent,
    BotLeaveEventActive,
    BotLeaveEventKick,
    BotMuteEvent,
    BotOfflineEventActive,
    BotOfflineEventDropped,
    BotOfflineEventForce,
    BotOnlineEvent,
    BotReloginEvent,
    BotUnmuteEvent,
    CommandExecutedEvent,
    FriendEvent,
    FriendInputStatusChangedEvent,
    FriendNickChangedEvent,
    FriendRecallEvent,
    GroupAllowAnonymousChatEvent,
    GroupAllowConfessTalkEvent,
    GroupAllowMemberInviteEvent,
    GroupEntranceAnnouncementChangeEvent,
    GroupEvent,
    GroupMuteAllEvent,
    GroupNameChangeEvent,
    GroupRecallEvent,
    MemberCardChangeEvent,
    MemberHonorChangeEvent,
    MemberJoinEvent,
    MemberJoinRequestEvent,
    MemberLeaveEventKick,
    MemberLeaveEventQuit,
    MemberMuteEvent,
    MemberPerm,
    MemberPermissionChangeEvent,
    MemberSpecialTitleChangeEvent,
    MemberUnmuteEvent,
    NewFriendRequestEvent,
    NudgeEvent,
    OtherClientOfflineEvent,
    OtherClientOnlineEvent,
    RequestEvent,
)
from graia.ariadne.event.network import InvalidRequest, RemoteException
