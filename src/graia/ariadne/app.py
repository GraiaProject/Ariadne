"""Ariadne 实例
"""
import asyncio
import base64
import importlib.metadata
import inspect
import io
import os
import sys
import time
from asyncio.events import AbstractEventLoop
from asyncio.tasks import Task
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Coroutine,
    Dict,
    Generator,
    Iterable,
    List,
    Literal,
    MutableSet,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

from graia.broadcast import Broadcast
from loguru import logger

from .adapter import Adapter, DefaultAdapter
from .context import enter_context, enter_message_send_context
from .dispatcher import ContextDispatcher
from .event.lifecycle import (
    AdapterLaunched,
    AdapterShutdowned,
    ApplicationLaunched,
    ApplicationShutdowned,
)
from .event.message import FriendMessage, GroupMessage, MessageEvent, TempMessage
from .message.chain import MessageChain
from .message.element import Source
from .model import (
    Announcement,
    AriadneStatus,
    BotMessage,
    CallMethod,
    ChatLogConfig,
    FileInfo,
    Friend,
    Group,
    GroupConfig,
    Member,
    MemberInfo,
    MiraiSession,
    Profile,
    Stranger,
    UploadMethod,
)
from .typing import SendMessageAction, SendMessageDict, SendMessageException
from .util import (
    app_ctx_manager,
    await_predicate,
    deprecated,
    inject_bypass_listener,
    inject_loguru_traceback,
    signal_handler,
    yield_with_timeout,
)

if TYPE_CHECKING:
    from .message.element import Image, Voice
    from .typing import R, T

ARIADNE_ASCII_LOGO = "\n".join(
    (
        r"                _           _             ",
        r"     /\        (_)         | |            ",
        r"    /  \   _ __ _  __ _  __| |_ __   ___  ",
        r"   / /\ \ | '__| |/ _` |/ _` | '_ \ / _ \ ",
        r"  / ____ \| |  | | (_| | (_| | | | |  __/ ",
        r" /_/    \_\_|  |_|\__,_|\__,_|_| |_|\___| ",
        r"",
    )
)


class AriadneMixin:
    """Ariadne 的 Mixin 基类."""

    broadcast: Broadcast
    adapter: Adapter
    mirai_session: MiraiSession
    chat_log_cfg: ChatLogConfig

    @property
    def session_key(self) -> Optional[str]:
        """返回 Ariadne 的 Mirai session key."""
        return self.mirai_session.session_key


class MessageMixin(AriadneMixin):
    """用于发送, 撤回, 获取消息的 Mixin 类."""

    default_send_action: SendMessageAction

    @app_ctx_manager
    async def getMessageFromId(self, messageId: int) -> MessageEvent:
        """从 消息 ID 提取 消息事件.

        Args:
            messageId (int): 消息 ID.

        Returns:
            MessageEvent: 提取的事件.
        """
        result = await self.adapter.call_api(
            "messageFromId",
            CallMethod.GET,
            {"sessionKey": self.session_key, "id": messageId},
        )
        return self.adapter.build_event(result)

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
            result = await self.adapter.call_api(
                "sendFriendMessage",
                CallMethod.POST,
                {
                    "sessionKey": self.session_key,
                    "target": int(target),
                    "messageChain": new_msg.dict()["__root__"],
                    **({"quote": quote.id if isinstance(quote, Source) else quote} if quote else {}),
                },
            )
            event: ActiveFriendMessage = ActiveFriendMessage(
                messageChain=MessageChain([Source(id=result["messageId"], time=datetime.now())]) + message,
                subject=(await RelationshipMixin.getFriend(self, int(target))),
            )
            with enter_context(self, event):
                self.broadcast.postEvent(event)
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
            result = await self.adapter.call_api(
                "sendGroupMessage",
                CallMethod.POST,
                {
                    "sessionKey": self.session_key,
                    "target": int(target),
                    "messageChain": new_msg.dict()["__root__"],
                    **({"quote": quote.id if isinstance(quote, Source) else quote} if quote else {}),
                },
            )
            event: ActiveGroupMessage = ActiveGroupMessage(
                messageChain=MessageChain([Source(id=result["messageId"], time=datetime.now())]) + message,
                subject=(await RelationshipMixin.getGroup(self, int(target))),
            )
            with enter_context(self, event):
                self.broadcast.postEvent(event)
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
            result = await self.adapter.call_api(
                "sendTempMessage",
                CallMethod.POST,
                {
                    "sessionKey": self.session_key,
                    "group": int(group),
                    "qq": int(target),
                    "messageChain": new_msg.dict()["__root__"],
                    **({"quote": quote.id if isinstance(quote, Source) else quote} if quote else {}),
                },
            )
            event: ActiveTempMessage = ActiveTempMessage(
                messageChain=MessageChain([Source(id=result["messageId"], time=datetime.now())]) + message,
                subject=(await RelationshipMixin.getMember(self, int(group), int(target))),
            )
            with enter_context(self, event):
                self.broadcast.postEvent(event)
            return BotMessage(messageId=result["messageId"], origin=message)

    @app_ctx_manager
    async def sendMessage(
        self,
        target: Union[MessageEvent, Group, Friend, Member],
        message: MessageChain,
        *,
        quote: Union[bool, int, Source, MessageChain] = False,
        action: SendMessageAction["T", "R"] = ...,
    ) -> Union["T", "R"]:
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
        data = {"message": message}
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
        data = await action.param(send_data)

        try:
            if isinstance(data["target"], Friend):
                val = await self.sendFriendMessage(**data)
            elif isinstance(data["target"], Group):
                val = await self.sendGroupMessage(**data)
            elif isinstance(data["target"], Member):
                val = await self.sendTempMessage(**data)
            else:
                raise NotImplementedError(f"Unable to send message with {target} as target.")
        except Exception as e:
            e.send_data = send_data
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
        await self.adapter.call_api(
            "sendNudge",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
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
        await self.adapter.call_api(
            "recall",
            CallMethod.POST,
            {"sessionKey": self.session_key, "target": target},
        )


class RelationshipMixin(AriadneMixin):
    """获取各种关系模型的 Mixin 类."""

    @app_ctx_manager
    async def getFriendList(self) -> List[Friend]:
        """获取本实例账号添加的好友列表.

        Returns:
            List[Friend]: 添加的好友.
        """
        result = await self.adapter.call_api(
            "friendList",
            CallMethod.GET,
            {"sessionKey": self.session_key},
        )
        return [Friend.parse_obj(i) for i in result]

    @app_ctx_manager
    async def getFriend(self, friend_id: int) -> Optional[Friend]:
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

    @app_ctx_manager
    async def getGroupList(self) -> List[Group]:
        """获取本实例账号加入的群组列表.

        Returns:
            List[Group]: 加入的群组.
        """
        result = await self.adapter.call_api(
            "groupList",
            CallMethod.GET,
            {"sessionKey": self.session_key},
        )
        return [Group.parse_obj(i) for i in result]

    @app_ctx_manager
    async def getGroup(self, group_id: int) -> Optional[Group]:
        """尝试从已知的群组唯一ID, 获取对应群组的信息; 可能返回 None.

        Args:
            group_id (int): 尝试获取的群组的唯一 ID.

        Returns:
            Group: 操作成功, 你得到了你应得的.
            None: 未能获取到.
        """
        data = await self.getGroupList()
        for i in data:
            if i.id == group_id:
                return i

    @app_ctx_manager
    async def getMemberList(self, group: Union[Group, int]) -> List[Member]:
        """尝试从已知的群组获取对应成员的列表.

        Args:
            group (Union[Group, int]): 已知的群组

        Returns:
            List[Member]: 群内成员的 Member 对象.
        """
        result = await self.adapter.call_api(
            "memberList",
            CallMethod.GET,
            {
                "sessionKey": self.session_key,
                "target": group.id if isinstance(group, Group) else group,
            },
        )
        return [Member.parse_obj(i) for i in result]

    @app_ctx_manager
    async def getMember(self, group: Union[Group, int], member_id: int) -> Member:
        """尝试从已知的群组唯一 ID 和已知的群组成员的 ID, 获取对应成员的信息.

        Args:
            group_id (Union[Group, int]): 已知的群组唯一 ID
            member_id (int): 已知的群组成员的 ID

        Returns:
            Member: 对应群成员对象
        """
        result = await self.adapter.call_api(
            "memberInfo",
            CallMethod.RESTGET,
            {
                "sessionKey": self.session_key,
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
        result = await self.adapter.call_api(
            "botProfile",
            CallMethod.GET,
            {"sessionKey": self.session_key},
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
        result = await self.adapter.call_api(
            "userProfile",
            CallMethod.GET,
            {
                "sessionKey": self.session_key,
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
        result = await self.adapter.call_api(
            "friendProfile",
            CallMethod.GET,
            {
                "sessionKey": self.session_key,
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
        result = await self.adapter.call_api(
            "memberProfile",
            CallMethod.GET,
            {"sessionKey": self.session_key, "target": group_id, "memberId": member_id},
        )
        return Profile.parse_obj(result)


class OperationMixin(AriadneMixin):
    """在各种关系模型中进行操作的 Mixin 类."""

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

        await self.adapter.call_api(
            "deleteFriend",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
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
        await self.adapter.call_api(
            "mute",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
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
        await self.adapter.call_api(
            "unmute",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
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
        await self.adapter.call_api(
            "muteAll",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
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
        await self.adapter.call_api(
            "unmuteAll",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
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
        await self.adapter.call_api(
            "kick",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
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
        await self.adapter.call_api(
            "quit",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
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

        await self.adapter.call_api(
            "setEssence",
            CallMethod.POST,
            {"sessionKey": self.session_key, "target": target},
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
        result = await self.adapter.call_api(
            "groupConfig",
            CallMethod.RESTGET,
            {
                "sessionKey": self.session_key,
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
        await self.adapter.call_api(
            "groupConfig",
            CallMethod.RESTPOST,
            {
                "sessionKey": self.session_key,
                "target": group.id if isinstance(group, Group) else group,
                "config": config.dict(exclude_unset=True, exclude_none=True),
            },
        )

    @deprecated("0.6.10")
    @app_ctx_manager
    async def getMemberInfo(
        self, member: Union[Member, int], group: Optional[Union[Group, int]] = None
    ) -> Member:
        """
        获取指定群组成员 (等价于 getMember, 但是更高效).

        Args:
            member (Union[Member, int]): 指定群成员, 可为 Member 实例, 若前设成立, 则不需要提供 group.
            group (Optional[Union[Group, int]], optional): 如果 member 为 Member 实例, 则不需要提供本项, 否则需要. 默认为 None.

        Raises:
            TypeError: 提供了错误的参数, 阅读有关文档得到问题原因

        Returns:
            Member: 指定群组成员
        """
        if not group and not isinstance(member, Member):
            raise TypeError("you should give a Member instance if you cannot give a Group instance to me.")
        if isinstance(member, Member) and not group:
            group: Group = member.group
        result = await self.adapter.call_api(
            "memberInfo",
            CallMethod.RESTGET,
            {
                "sessionKey": self.session_key,
                "target": group.id if isinstance(group, Group) else group,
                "memberId": member.id if isinstance(member, Member) else member,
            },
        )

        return Member.parse_obj(result)

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
        if not group and not isinstance(member, Member):
            raise TypeError("you should give a Member instance if you cannot give a Group instance to me.")
        if isinstance(member, Member) and not group:
            group: Group = member.group
        await self.adapter.call_api(
            "memberInfo",
            CallMethod.RESTPOST,
            {
                "sessionKey": self.session_key,
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
        if not group and not isinstance(member, Member):
            raise TypeError("you should give a Member instance if you cannot give a Group instance to me.")
        if isinstance(member, Member) and not group:
            group: Group = member.group

        await self.adapter.call_api(
            "memberAdmin",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
                "target": group.id if isinstance(group, Group) else group,
                "memberId": member.id if isinstance(member, Member) else member,
                "assign": assign,
            },
        )

    @app_ctx_manager
    async def registerCommand(
        self, name: str, alias: Iterable[str] = (), usage: str = "", description: str = ""
    ) -> None:
        """注册一个指令

        Args:
            name (str): 指令名
            alias (Iterable[str], optional): 指令别名. Defaults to ().
            usage (str, optional): 使用方法字符串. Defaults to "".
            description (str, optional): 描述字符串. Defaults to "".

        """
        await self.adapter.call_api(
            "cmd/register",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
                "name": name,
                "alias": alias,
                "usage": usage,
                "description": description,
            },
        )

    @app_ctx_manager
    async def executeCommand(self, command: Union[str, Iterable[str]]) -> None:
        """执行一条指令

        Args:
            command (Union[str, Iterable[str]]): 指令字符串.

        """
        if isinstance(command, str):
            command = command.split(" ")
        await self.adapter.call_api(
            "cmd/execute", CallMethod.POST, {"sessionKey": self.session_key, "command": command}
        )


class AnnouncementMixin(AriadneMixin):
    """对群公告进行操作的 Mixin 类."""

    async def getAnnouncementIterator(
        self,
        target: Union[Group, int],
        offset: Optional[int] = 0,
        size: Optional[int] = 10,
    ) -> Generator[Announcement, None, None]:
        """
        获取群公告列表.

        Args:
            target (Union[Group, int]): 指定的群组.
            offset (Optional[int], optional): 起始偏移量. 默认为 0.
            size (Optional[int], optional): 列表大小. 默认为 10.

        Returns:
            Generator[Announcement, None, None]: 列出群组下所有的公告.
        """
        target = int(target)
        current_offset = offset
        cache: List[FileInfo] = []
        while True:
            while cache:
                yield cache[0]
                cache.pop(0)
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

        result = await self.adapter.call_api(
            "anno/list",
            CallMethod.GET,
            {
                "sessionKey": self.session_key,
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
            "sessionKey": self.session_key,
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

        result = await self.adapter.call_api(
            "anno/publish",
            CallMethod.POST,
            data,
        )
        return Announcement.parse_obj(result)

    @app_ctx_manager
    async def deleteAnnouncement(self, target: Union[Group, int], anno: Union[Announcement, int]) -> None:
        """"""


class FileMixin(AriadneMixin):
    """用于对文件进行各种操作的 Mixin 类."""

    async def getFileIterator(
        self,
        target: Union[Group, int],
        id: str = "",
        offset: Optional[int] = 0,
        size: Optional[int] = 1,
        with_download_info: bool = False,
    ) -> Generator[FileInfo, None, None]:
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
            Generator[FileInfo, None, None]: 文件信息生成器.
        """
        target = int(target)
        current_offset = offset
        cache: List[FileInfo] = []
        while True:
            while cache:
                yield cache[0]
                cache.pop(0)
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

        result = await self.adapter.call_api(
            "file/list",
            CallMethod.GET,
            {
                "sessionKey": self.session_key,
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

        result = await self.adapter.call_api(
            "file/info",
            CallMethod.GET,
            {
                "sessionKey": self.session_key,
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

        result = await self.adapter.call_api(
            "file/mkdir",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
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

        await self.adapter.call_api(
            "file/delete",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
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

        await self.adapter.call_api(
            "file/move",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
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

        await self.adapter.call_api(
            "file/rename",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
                "id": id,
                "target": target,
                "renameTo": dest_name,
            },
        )

    @app_ctx_manager
    async def uploadFile(
        self,
        data: Union[bytes, io.IOBase, os.PathLike],
        method: Union[str, UploadMethod] = None,
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

        result = await self.adapter.call_api(
            "file/upload",
            CallMethod.MULTIPART,
            {
                "sessionKey": self.session_key,
                "type": method,
                "target": str(target),
                "path": path,
                "file": (data, {"filename": name} if name else {}),
            },
        )

        return FileInfo.parse_obj(result)


class MultimediaMixin(AriadneMixin):
    """用于与多媒体信息交互的 Mixin 类."""

    @app_ctx_manager
    async def uploadImage(
        self, data: Union[bytes, io.IOBase, os.PathLike], method: Union[str, UploadMethod] = None
    ) -> "Image":
        """上传一张图片到远端服务器, 需要提供: 图片的原始数据(bytes), 图片的上传类型.
        Args:
            image_bytes (Union[bytes, io.IOBase, os.PathLike]): 图片的原始数据
            method (str | UploadMethod, optional): 图片的上传类型, 可从上下文推断
        Returns:
            Image: 生成的图片消息元素
        """
        from .context import upload_method_ctx
        from .message.element import Image

        method = str(method or upload_method_ctx.get()).lower()

        if isinstance(data, os.PathLike):
            data = open(data, "rb")

        result = await self.adapter.call_api(
            "uploadImage",
            CallMethod.MULTIPART,
            {
                "sessionKey": self.session_key,
                "type": method,
                "img": data,
            },
        )

        return Image.parse_obj(result)

    @app_ctx_manager
    async def uploadVoice(
        self, data: Union[bytes, io.IOBase, os.PathLike], method: Union[str, UploadMethod] = None
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

        result = await self.adapter.call_api(
            "uploadVoice",
            CallMethod.MULTIPART,
            {
                "sessionKey": self.session_key,
                "type": method,
                "voice": data,
            },
        )

        return Voice.parse_obj(result)


class Ariadne(MessageMixin, RelationshipMixin, OperationMixin, AnnouncementMixin, FileMixin, MultimediaMixin):
    """
    艾莉亚德妮 (Ariadne).

    面向 `mirai-api-http` 接口的实际功能实现.

    你的应用大多都围绕着本类及本类的实例展开.

    Attributes:
        broadcast (Broadcast): 被指定的, 外置的事件系统, 即 `Broadcast Control`,
            通常你不需要干涉该属性;
        adapter (Adapter): 后端适配器, 负责实际与 `mirai-api-http` 进行交互.
    """

    loop: AbstractEventLoop
    broadcast: Broadcast
    adapter: Adapter
    status: AriadneStatus
    running: ClassVar[MutableSet["Ariadne"]] = set()

    def __init__(
        self,
        connect_info: Union[Adapter, MiraiSession],
        *,
        loop: Optional[AbstractEventLoop] = None,
        broadcast: Optional[Broadcast] = None,
        max_retry: int = -1,
        chat_log_config: Optional[Union[ChatLogConfig, Literal[False]]] = None,
        use_loguru_traceback: Optional[bool] = True,
        use_bypass_listener: Optional[bool] = False,
        disable_telemetry: bool = False,
        disable_logo: bool = False,
    ):
        """
        初始化 Ariadne.

        Args:
            connect_info (Union[Adapter, MiraiSession]): 提供与 `mirai-api-http` 交互的信息.
            loop (AbstractEventLoop, optional): 事件循环.
            broadcast (Broadcast, optional): 被指定的, 外置的事件系统, 即 `Broadcast Control` 实例.
            chat_log_config (Optional[Union[ChatLogConfig, Literal[False]]]): 聊天日志的配置. \
            请移步 [ChatLogConfig][graia.ariadne.model.ChatLogConfig] 查看使用方法. \
            设置为 False 则会完全禁用聊天日志.
            use_loguru_traceback (bool): 是否注入 loguru 以获得对 traceback.print_exception() 与 sys.excepthook 的完全控制.
            use_bypass_listener (bool): 是否注入 BypassListener 以获得子事件监听支持.
            disable_telemetry (bool): 是否禁用版本记录.
            disable_logo (bool): 是否禁用 logo 显示.
        """
        if broadcast:
            loop = broadcast.loop
        elif isinstance(connect_info, Adapter):
            broadcast = connect_info.broadcast
            loop = broadcast.loop
        if not loop:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
        self.loop = loop
        self.broadcast: Broadcast = broadcast or Broadcast(loop=self.loop)
        self.adapter: Adapter = (
            connect_info
            if isinstance(connect_info, Adapter)
            else DefaultAdapter(self.broadcast, connect_info)
        )
        self.mirai_session: MiraiSession = self.adapter.mirai_session

        self.daemon_task: Optional[Task] = None
        self.status: AriadneStatus = AriadneStatus.STOP
        self.remote_version: str = ""
        self.max_retry: int = max_retry
        self.disable_telemetry: bool = disable_telemetry
        self.disable_logo: bool = disable_logo
        self.info: Dict[type, object] = {
            Ariadne: self,
            Broadcast: self.broadcast,
            AbstractEventLoop: self.loop,
            Adapter: self.adapter,
            MiraiSession: self.mirai_session,
        }

        chat_log_enabled = chat_log_config is not False
        self.chat_log_cfg: ChatLogConfig = chat_log_config or ChatLogConfig(enabled=chat_log_enabled)

        from .util.send import Strict

        self.default_send_action = Strict

        if use_bypass_listener:
            inject_bypass_listener(self.broadcast)
        if use_loguru_traceback:
            inject_loguru_traceback(self.loop)

        if ContextDispatcher not in self.broadcast.finale_dispatchers:
            self.broadcast.finale_dispatchers.append(ContextDispatcher)

    def create(self, cls: Type["T"], reuse: bool = True) -> "T":
        """利用 Ariadne 已有的信息协助创建实例.

        Args:
            cls (Type[T]): 需要创建的类.
            reuse (bool, optional): 是否允许复用, 默认为 True.

        Returns:
            T: 创建的类.
        """
        self.info: Dict[Type["T"], "T"]
        if cls in self.info.keys():
            return self.info[cls]
        call_args: list = []
        call_kwargs: Dict[str, Any] = {}

        init_sig = inspect.signature(cls)

        for name, param in init_sig.parameters.items():
            if param.annotation in self.info.keys() and param.kind not in (
                param.VAR_KEYWORD,
                param.VAR_POSITIONAL,
            ):
                param_obj = self.info.get(param.annotation, param.default)
                if param_obj is param.empty:
                    param_obj = self.create(param.annotation, reuse=True)
                if param.kind is param.POSITIONAL_ONLY:
                    call_args.append(param_obj)
                else:
                    call_kwargs[name] = param_obj

        obj: "T" = cls(*call_args, **call_kwargs)
        if reuse:
            self.info[cls] = obj
        return obj

    async def daemon(self, retry_interval: float = 5.0):
        """Ariadne 生命周期管理的具体方法.

        Args:
            retry_interval (float, optional): Adapter 重连间隔 (s). 默认 5.0.
        """
        from .event.message import MessageEvent
        from .event.mirai import FriendEvent, GroupEvent

        retry_cnt: int = 0

        logger.debug("Ariadne daemon started.")

        while self.status in {AriadneStatus.RUNNING, AriadneStatus.LAUNCH}:
            try:
                await asyncio.wait_for(self.adapter.start(), timeout=retry_interval)
                logger.success("daemon: adapter started")
                self.broadcast.postEvent(AdapterLaunched(self))
                async for event in yield_with_timeout(
                    self.adapter.event_queue.get,
                    lambda: (
                        self.adapter.running and self.status in {AriadneStatus.RUNNING, AriadneStatus.LAUNCH}
                    ),
                ):
                    with enter_context(self, event):
                        sys.audit("AriadnePostRemoteEvent", event)
                        if isinstance(event, MessageEvent):
                            if event.messageChain.onlyContains(Source):  # Contains unsupported type
                                event.messageChain.append("<! 不支持的消息类型 !>")
                        if isinstance(event, FriendEvent):
                            with enter_message_send_context(UploadMethod.Friend):
                                self.broadcast.postEvent(event)
                        elif isinstance(event, GroupEvent):
                            with enter_message_send_context(UploadMethod.Group):
                                self.broadcast.postEvent(event)
                        else:
                            self.broadcast.postEvent(event)
            except asyncio.exceptions.TimeoutError:
                logger.critical("Timeout when connecting to mirai-api-http. Configuration problem?")
            except Exception as e:
                logger.exception(e)
            self.broadcast.postEvent(AdapterShutdowned(self))
            if retry_cnt == self.max_retry:
                logger.critical(f"Max retry exceeded: {self.max_retry}. Stop Ariadne.")
                logger.warning("Press Ctrl-C to confirm exit.")
                break
            if self.status in {AriadneStatus.RUNNING, AriadneStatus.LAUNCH}:
                if not self.adapter.mirai_session.session_key or self.adapter.mirai_session.single_mode:
                    retry_cnt += 1
                else:
                    retry_cnt = 0
                await self.adapter.stop()
                logger.warning(f"daemon: adapter down, restart in {retry_interval}s")
                await asyncio.sleep(retry_interval)
                logger.info("daemon: restarting adapter")

        logger.debug("Ariadne daemon stopped.")

        exceptions: List[Tuple[Type[Exception], tuple]] = []

        logger.info("Stopping Ariadne...")
        self.status = AriadneStatus.CLEANUP
        for t in asyncio.all_tasks(self.loop):
            if t is asyncio.current_task(self.loop):
                continue
            coro: Coroutine = t.get_coro()
            try:
                if coro.__qualname__ in ("Broadcast.Executor", "print_track_async.<locals>.wrapper"):
                    t.cancel()
                    logger.debug(f"Cancelling {t.get_name()} wrapping {coro.__qualname__}")
            except Exception as e:
                exceptions.append((e.__class__, e.args))

        logger.info("Posting Ariadne shutdown event...")

        await self.broadcast.layered_scheduler(
            listener_generator=self.broadcast.default_listener_generator(ApplicationShutdowned),
            event=ApplicationShutdowned(self),
        )

        self.running.remove(self)

        logger.info("Stopping adapter...")
        await self.adapter.stop()
        logger.success(f"Adapter {self.adapter.__class__.__name__} stopped.")
        self.status = AriadneStatus.STOP
        logger.success("Stopped Ariadne.")
        return exceptions

    async def launch(self):
        """启动 Ariadne."""
        if self.status is AriadneStatus.STOP:
            self.status = AriadneStatus.LAUNCH

            # Logo
            if not self.disable_logo:
                logger.opt(colors=True, raw=True).info(f"<cyan>{ARIADNE_ASCII_LOGO}</>")

            # Telemetry
            if not self.disable_telemetry:
                official: List[Tuple[str, str]] = []
                community: List[str] = []
                for dist in importlib.metadata.distributions():
                    name: str = dist.metadata["Name"]
                    version: str = dist.version
                    if name.startswith("graia-"):
                        official.append((" ".join(name.split("-")[1:]).title(), version))
                    elif name.startswith("graiax-"):
                        community.append((" ".join(name.split("-")).title(), version))

                for name, version in official:
                    logger.opt(colors=True, raw=True).info(
                        f"<magenta>{name}</> version: <yellow>{version}</>\n"
                    )
                for name, version in community:
                    logger.opt(colors=True, raw=True).info(f"<cyan>{name}</> version: <yellow>{version}</>\n")

            logger.info("Launching app...")
            start_time = time.time()

            if self.chat_log_cfg.enabled:
                self.chat_log_cfg.initialize(self)

            if ContextDispatcher not in self.broadcast.finale_dispatchers:
                self.broadcast.finale_dispatchers.append(ContextDispatcher)

            self.daemon_task = self.loop.create_task(self.daemon(), name="ariadne_daemon")
            if "reverse" not in self.adapter.tags:
                await await_predicate(
                    lambda: self.adapter.mirai_session.session_key or self.adapter.mirai_session.single_mode,
                    0.0001,
                )
            await await_predicate(lambda: self.adapter.running, 0.0001)

            self.status = AriadneStatus.RUNNING
            self.running.add(self)

            self.remote_version = await self.getVersion()
            logger.success(f"Remote version: {self.remote_version}")
            if not self.remote_version.startswith("2"):
                raise RuntimeError(f"You are using an unsupported version: {self.remote_version}!")
            logger.success(f"Application launched with {time.time() - start_time:.2}s")

            await self.broadcast.layered_scheduler(
                listener_generator=self.broadcast.default_listener_generator(ApplicationLaunched),
                event=ApplicationLaunched(self),
            )

    async def stop(self):
        """请求停止 Ariadne."""
        if self.status is AriadneStatus.RUNNING:
            self.status = AriadneStatus.SHUTDOWN
            await await_predicate(lambda: self.status in {AriadneStatus.CLEANUP, AriadneStatus.STOP})

    async def join(self):
        """等待直到 Ariadne 真正停止.
        不要在与 Broadcast 相关的任务中使用.
        """
        if self.status in {AriadneStatus.RUNNING, AriadneStatus.LAUNCH}:
            await self.stop()
        await await_predicate(lambda: self.status is AriadneStatus.STOP)
        await self.daemon_task

    async def lifecycle(self):
        """以 async 阻塞方式启动 Ariadne 并等待其停止."""

        def sig_handler(*_):
            if self.status is AriadneStatus.RUNNING:
                self.status = AriadneStatus.SHUTDOWN

        signal_handler(sig_handler)
        await self.launch()
        await self.daemon_task

    def launch_blocking(self):
        """以阻塞方式启动 Ariadne 并等待其停止."""
        try:
            self.loop.run_until_complete(self.lifecycle())
        except KeyboardInterrupt:
            pass
        self.loop.run_until_complete(self.join())

    @app_ctx_manager
    async def getVersion(self, auto_set: bool = True) -> str:
        """获取后端 Mirai HTTP API 版本.

        Args:
            auto_set (bool, optional): 自动设置到实例的 MiraiSession.version. 默认为 True.

        Returns:
            str: 版本信息.
        """
        if self.mirai_session.version:
            return self.mirai_session.version
        result = await self.adapter.call_api("about", CallMethod.GET)
        version = result["version"]
        if auto_set:
            self.mirai_session.version = version
        return version

    async def __aenter__(self) -> "Ariadne":
        await self.launch()

        return self

    async def __aexit__(self, *exc):
        await self.join()

    @property
    def account(self) -> Optional[int]:
        """获取当前实例对应 MiraiSession 的账号."""
        return self.adapter.mirai_session.account
