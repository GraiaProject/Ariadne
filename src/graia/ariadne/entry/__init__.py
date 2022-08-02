"""Ariadne 一站式导入的提供模块"""

import contextlib

from ..app import Ariadne as Ariadne
from ..connection.config import HttpClientConfig as HttpClientConfig
from ..connection.config import HttpServerConfig as HttpServerConfig
from ..connection.config import WebsocketClientConfig as WebsocketClientConfig
from ..connection.config import WebsocketServerConfig as WebsocketServerConfig
from ..connection.config import config as config
from ..connection.util import UploadMethod as UploadMethod
from ..context import ariadne_ctx as ariadne_ctx
from ..context import broadcast_ctx as broadcast_ctx
from ..context import event_ctx as event_ctx
from ..context import event_loop_ctx as event_loop_ctx
from ..context import upload_method_ctx as upload_method_ctx
from ..dispatcher import ContextDispatcher as ContextDispatcher
from ..dispatcher import MessageChainDispatcher as MessageChainDispatcher
from ..dispatcher import SourceDispatcher as SourceDispatcher
from ..exception import AccountMuted as AccountMuted
from ..exception import AccountNotFound as AccountNotFound
from ..exception import InvalidArgument as InvalidArgument
from ..exception import InvalidEventTypeDefinition as InvalidEventTypeDefinition
from ..exception import InvalidSession as InvalidSession
from ..exception import InvalidVerifyKey as InvalidVerifyKey
from ..exception import MessageTooLong as MessageTooLong
from ..exception import UnknownError as UnknownError
from ..exception import UnknownTarget as UnknownTarget
from ..exception import UnVerifiedSession as UnVerifiedSession
from ..model import *
from ..util.async_exec import cpu_bound as cpu_bound
from ..util.async_exec import io_bound as io_bound
from ..util.cooldown import CoolDown as CoolDown
from ..util.send import Bypass as Bypass
from ..util.send import Ignore as Ignore
from ..util.send import Safe as Safe
from ..util.send import Strict as Strict
from ..util.validator import Certain as Certain
from ..util.validator import CertainFriend as CertainFriend
from ..util.validator import CertainGroup as CertainGroup
from ..util.validator import CertainMember as CertainMember
from ..util.validator import Quoting as Quoting
from . import event as event
from . import message as message
from .broadcast import *
from .event import AccountLaunch as AccountLaunch
from .event import AccountShutdown as AccountShutdown
from .event import ActiveFriendMessage as ActiveFriendMessage
from .event import ActiveGroupMessage as ActiveGroupMessage
from .event import ActiveMessage as ActiveMessage
from .event import ActiveStrangerMessage as ActiveStrangerMessage
from .event import ActiveTempMessage as ActiveTempMessage
from .event import ApplicationLaunch as ApplicationLaunch
from .event import ApplicationShutdown as ApplicationShutdown
from .event import BotEvent as BotEvent
from .event import BotGroupPermissionChangeEvent as BotGroupPermissionChangeEvent
from .event import BotInvitedJoinGroupRequestEvent as BotInvitedJoinGroupRequestEvent
from .event import BotJoinGroupEvent as BotJoinGroupEvent
from .event import BotLeaveEventActive as BotLeaveEventActive
from .event import BotLeaveEventKick as BotLeaveEventKick
from .event import BotMuteEvent as BotMuteEvent
from .event import BotOfflineEventActive as BotOfflineEventActive
from .event import BotOfflineEventDropped as BotOfflineEventDropped
from .event import BotOfflineEventForce as BotOfflineEventForce
from .event import BotOnlineEvent as BotOnlineEvent
from .event import BotReloginEvent as BotReloginEvent
from .event import BotUnmuteEvent as BotUnmuteEvent
from .event import ClientKind as ClientKind
from .event import CommandExecutedEvent as CommandExecutedEvent
from .event import FriendEvent as FriendEvent
from .event import FriendInputStatusChangedEvent as FriendInputStatusChangedEvent
from .event import FriendMessage as FriendMessage
from .event import FriendNickChangedEvent as FriendNickChangedEvent
from .event import FriendRecallEvent as FriendRecallEvent
from .event import FriendSyncMessage as FriendSyncMessage
from .event import GroupAllowAnonymousChatEvent as GroupAllowAnonymousChatEvent
from .event import GroupAllowConfessTalkEvent as GroupAllowConfessTalkEvent
from .event import GroupAllowMemberInviteEvent as GroupAllowMemberInviteEvent
from .event import (
    GroupEntranceAnnouncementChangeEvent as GroupEntranceAnnouncementChangeEvent,
)
from .event import GroupEvent as GroupEvent
from .event import GroupMessage as GroupMessage
from .event import GroupMuteAllEvent as GroupMuteAllEvent
from .event import GroupNameChangeEvent as GroupNameChangeEvent
from .event import GroupRecallEvent as GroupRecallEvent
from .event import GroupSyncMessage as GroupSyncMessage
from .event import MemberCardChangeEvent as MemberCardChangeEvent
from .event import MemberHonorChangeEvent as MemberHonorChangeEvent
from .event import MemberJoinEvent as MemberJoinEvent
from .event import MemberJoinRequestEvent as MemberJoinRequestEvent
from .event import MemberLeaveEventKick as MemberLeaveEventKick
from .event import MemberLeaveEventQuit as MemberLeaveEventQuit
from .event import MemberMuteEvent as MemberMuteEvent
from .event import MemberPermissionChangeEvent as MemberPermissionChangeEvent
from .event import MemberSpecialTitleChangeEvent as MemberSpecialTitleChangeEvent
from .event import MemberUnmuteEvent as MemberUnmuteEvent
from .event import MessageEvent as MessageEvent
from .event import MiraiEvent as MiraiEvent
from .event import NewFriendRequestEvent as NewFriendRequestEvent
from .event import NudgeEvent as NudgeEvent
from .event import OtherClientOfflineEvent as OtherClientOfflineEvent
from .event import OtherClientOnlineEvent as OtherClientOnlineEvent
from .event import RequestEvent as RequestEvent
from .event import StrangerMessage as StrangerMessage
from .event import StrangerSyncMessage as StrangerSyncMessage
from .event import SyncMessage as SyncMessage
from .event import TempMessage as TempMessage
from .event import TempSyncMessage as TempSyncMessage
from .message import App as App
from .message import Arg as Arg
from .message import ArgResult as ArgResult
from .message import ArgumentMatch as ArgumentMatch
from .message import At as At
from .message import AtAll as AtAll
from .message import Bypass as Bypass
from .message import Commander as Commander
from .message import Compose as Compose
from .message import ContainKeyword as ContainKeyword
from .message import DetectPrefix as DetectPrefix
from .message import DetectSuffix as DetectSuffix
from .message import Dice as Dice
from .message import Element as Element
from .message import ElementMatch as ElementMatch
from .message import Face as Face
from .message import File as File
from .message import FlashImage as FlashImage
from .message import Formatter as Formatter
from .message import Forward as Forward
from .message import ForwardNode as ForwardNode
from .message import FullMatch as FullMatch
from .message import FuzzyDispatcher as FuzzyDispatcher
from .message import FuzzyMatch as FuzzyMatch
from .message import Ignore as Ignore
from .message import Image as Image
from .message import ImageType as ImageType
from .message import Match as Match
from .message import MatchContent as MatchContent
from .message import MatchRegex as MatchRegex
from .message import MatchResult as MatchResult
from .message import MatchTemplate as MatchTemplate
from .message import Mention as Mention
from .message import MentionMe as MentionMe
from .message import MessageChain as MessageChain
from .message import MultimediaElement as MultimediaElement
from .message import MusicShare as MusicShare
from .message import Plain as Plain
from .message import Poke as Poke
from .message import PokeMethods as PokeMethods
from .message import Quote as Quote
from .message import RegexMatch as RegexMatch
from .message import RegexResult as RegexResult
from .message import Safe as Safe
from .message import Slot as Slot
from .message import Source as Source
from .message import Sparkle as Sparkle
from .message import Strict as Strict
from .message import Twilight as Twilight
from .message import UnionMatch as UnionMatch
from .message import Voice as Voice
from .message import WildcardMatch as WildcardMatch
from .saya import *
from .scheduler import *

with contextlib.suppress(ImportError):
    from ..console import Console as Console
    from ..console.saya import ConsoleBehaviour as ConsoleBehaviour
    from ..console.saya import ConsoleSchema as ConsoleSchema

# We are using the star import because the dependencies may not be present
