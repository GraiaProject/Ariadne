"""Ariadne 事件相关的导入集合"""

# no error

from graia.ariadne.event import MiraiEvent as MiraiEvent
from graia.ariadne.event.lifecycle import (
    AdapterLaunched as AdapterLaunched,
    AdapterShutdowned as AdapterShutdowned,
    ApplicationLaunched as ApplicationLaunched,
    ApplicationLifecycleEvent as ApplicationLifecycleEvent,
    ApplicationShutdowned as ApplicationShutdowned,
)
from graia.ariadne.event.message import (
    FriendMessage as FriendMessage,
    GroupMessage as GroupMessage,
    OtherClientMessage as OtherClientMessage,
    StrangerMessage as StrangerMessage,
    TempMessage as TempMessage,
)
from graia.ariadne.event.mirai import (
    BotEvent as BotEvent,
    BotGroupPermissionChangeEvent as BotGroupPermissionChangeEvent,
    BotInvitedJoinGroupRequestEvent as BotInvitedJoinGroupRequestEvent,
    BotJoinGroupEvent as BotJoinGroupEvent,
    BotLeaveEventActive as BotLeaveEventActive,
    BotLeaveEventKick as BotLeaveEventKick,
    BotMuteEvent as BotMuteEvent,
    BotOfflineEventActive as BotOfflineEventActive,
    BotOfflineEventDropped as BotOfflineEventDropped,
    BotOfflineEventForce as BotOfflineEventForce,
    BotOnlineEvent as BotOnlineEvent,
    BotReloginEvent as BotReloginEvent,
    BotUnmuteEvent as BotUnmuteEvent,
    CommandExecutedEvent as CommandExecutedEvent,
    FriendEvent as FriendEvent,
    FriendInputStatusChangedEvent as FriendInputStatusChangedEvent,
    FriendNickChangedEvent as FriendNickChangedEvent,
    FriendRecallEvent as FriendRecallEvent,
    GroupAllowAnonymousChatEvent as GroupAllowAnonymousChatEvent,
    GroupAllowConfessTalkEvent as GroupAllowConfessTalkEvent,
    GroupAllowMemberInviteEvent as GroupAllowMemberInviteEvent,
    GroupEntranceAnnouncementChangeEvent as GroupEntranceAnnouncementChangeEvent,
    GroupEvent as GroupEvent,
    GroupMuteAllEvent as GroupMuteAllEvent,
    GroupNameChangeEvent as GroupNameChangeEvent,
    GroupRecallEvent as GroupRecallEvent,
    MemberCardChangeEvent as MemberCardChangeEvent,
    MemberHonorChangeEvent as MemberHonorChangeEvent,
    MemberJoinEvent as MemberJoinEvent,
    MemberJoinRequestEvent as MemberJoinRequestEvent,
    MemberLeaveEventKick as MemberLeaveEventKick,
    MemberLeaveEventQuit as MemberLeaveEventQuit,
    MemberMuteEvent as MemberMuteEvent,
    MemberPerm as MemberPerm,
    MemberPermissionChangeEvent as MemberPermissionChangeEvent,
    MemberSpecialTitleChangeEvent as MemberSpecialTitleChangeEvent,
    MemberUnmuteEvent as MemberUnmuteEvent,
    NewFriendRequestEvent as NewFriendRequestEvent,
    NudgeEvent as NudgeEvent,
    OtherClientOfflineEvent as OtherClientOfflineEvent,
    OtherClientOnlineEvent as OtherClientOnlineEvent,
    RequestEvent as RequestEvent,
)
from graia.ariadne.event.network import InvalidRequest as InvalidRequest, RemoteException as RemoteException
