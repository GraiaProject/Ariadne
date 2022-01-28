"""Ariadne 事件相关的导入集合"""

# no error

from graia.ariadne.event import MiraiEvent as MiraiEvent
from graia.ariadne.event.lifecycle import AdapterLaunched as AdapterLaunched
from graia.ariadne.event.lifecycle import AdapterShutdowned as AdapterShutdowned
from graia.ariadne.event.lifecycle import ApplicationLaunched as ApplicationLaunched
from graia.ariadne.event.lifecycle import (
    ApplicationLifecycleEvent as ApplicationLifecycleEvent,
)
from graia.ariadne.event.lifecycle import ApplicationShutdowned as ApplicationShutdowned
from graia.ariadne.event.message import FriendMessage as FriendMessage
from graia.ariadne.event.message import GroupMessage as GroupMessage
from graia.ariadne.event.message import OtherClientMessage as OtherClientMessage
from graia.ariadne.event.message import StrangerMessage as StrangerMessage
from graia.ariadne.event.message import TempMessage as TempMessage
from graia.ariadne.event.mirai import BotEvent as BotEvent
from graia.ariadne.event.mirai import (
    BotGroupPermissionChangeEvent as BotGroupPermissionChangeEvent,
)
from graia.ariadne.event.mirai import (
    BotInvitedJoinGroupRequestEvent as BotInvitedJoinGroupRequestEvent,
)
from graia.ariadne.event.mirai import BotJoinGroupEvent as BotJoinGroupEvent
from graia.ariadne.event.mirai import BotLeaveEventActive as BotLeaveEventActive
from graia.ariadne.event.mirai import BotLeaveEventKick as BotLeaveEventKick
from graia.ariadne.event.mirai import BotMuteEvent as BotMuteEvent
from graia.ariadne.event.mirai import BotOfflineEventActive as BotOfflineEventActive
from graia.ariadne.event.mirai import BotOfflineEventDropped as BotOfflineEventDropped
from graia.ariadne.event.mirai import BotOfflineEventForce as BotOfflineEventForce
from graia.ariadne.event.mirai import BotOnlineEvent as BotOnlineEvent
from graia.ariadne.event.mirai import BotReloginEvent as BotReloginEvent
from graia.ariadne.event.mirai import BotUnmuteEvent as BotUnmuteEvent
from graia.ariadne.event.mirai import CommandExecutedEvent as CommandExecutedEvent
from graia.ariadne.event.mirai import FriendEvent as FriendEvent
from graia.ariadne.event.mirai import (
    FriendInputStatusChangedEvent as FriendInputStatusChangedEvent,
)
from graia.ariadne.event.mirai import FriendNickChangedEvent as FriendNickChangedEvent
from graia.ariadne.event.mirai import FriendRecallEvent as FriendRecallEvent
from graia.ariadne.event.mirai import (
    GroupAllowAnonymousChatEvent as GroupAllowAnonymousChatEvent,
)
from graia.ariadne.event.mirai import (
    GroupAllowConfessTalkEvent as GroupAllowConfessTalkEvent,
)
from graia.ariadne.event.mirai import (
    GroupAllowMemberInviteEvent as GroupAllowMemberInviteEvent,
)
from graia.ariadne.event.mirai import (
    GroupEntranceAnnouncementChangeEvent as GroupEntranceAnnouncementChangeEvent,
)
from graia.ariadne.event.mirai import GroupEvent as GroupEvent
from graia.ariadne.event.mirai import GroupMuteAllEvent as GroupMuteAllEvent
from graia.ariadne.event.mirai import GroupNameChangeEvent as GroupNameChangeEvent
from graia.ariadne.event.mirai import GroupRecallEvent as GroupRecallEvent
from graia.ariadne.event.mirai import MemberCardChangeEvent as MemberCardChangeEvent
from graia.ariadne.event.mirai import MemberHonorChangeEvent as MemberHonorChangeEvent
from graia.ariadne.event.mirai import MemberJoinEvent as MemberJoinEvent
from graia.ariadne.event.mirai import MemberJoinRequestEvent as MemberJoinRequestEvent
from graia.ariadne.event.mirai import MemberLeaveEventKick as MemberLeaveEventKick
from graia.ariadne.event.mirai import MemberLeaveEventQuit as MemberLeaveEventQuit
from graia.ariadne.event.mirai import MemberMuteEvent as MemberMuteEvent
from graia.ariadne.event.mirai import MemberPerm as MemberPerm
from graia.ariadne.event.mirai import (
    MemberPermissionChangeEvent as MemberPermissionChangeEvent,
)
from graia.ariadne.event.mirai import (
    MemberSpecialTitleChangeEvent as MemberSpecialTitleChangeEvent,
)
from graia.ariadne.event.mirai import MemberUnmuteEvent as MemberUnmuteEvent
from graia.ariadne.event.mirai import NewFriendRequestEvent as NewFriendRequestEvent
from graia.ariadne.event.mirai import NudgeEvent as NudgeEvent
from graia.ariadne.event.mirai import OtherClientOfflineEvent as OtherClientOfflineEvent
from graia.ariadne.event.mirai import OtherClientOnlineEvent as OtherClientOnlineEvent
from graia.ariadne.event.mirai import RequestEvent as RequestEvent
