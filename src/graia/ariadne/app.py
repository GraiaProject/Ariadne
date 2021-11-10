import asyncio
import time
from asyncio.events import AbstractEventLoop
from asyncio.exceptions import CancelledError
from asyncio.tasks import Task
from typing import TYPE_CHECKING, List, Literal, Optional, Union

from graia.broadcast import Broadcast
from loguru import logger

from .adapter import Adapter, DefaultAdapter
from .context import enter_message_send_context
from .event import MiraiEvent
from .event.lifecycle import (
    AdapterLaunched,
    AdapterShutdowned,
    ApplicationLaunched,
    ApplicationShutdowned,
)
from .event.message import FriendMessage, GroupMessage, MessageEvent, TempMessage
from .message.element import Source
from .util import inject_bypass_listener, inject_loguru_traceback

if TYPE_CHECKING:
    from .message.element import Image, Voice

from .message.chain import MessageChain
from .model import (
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
    UploadMethod,
)
from .util import ApplicationMiddlewareDispatcher, app_ctx_manager


class AriadneMixin:
    """Ariadne 的 Mixin 基类."""

    broadcast: Broadcast
    adapter: Adapter
    mirai_session: MiraiSession

    @property
    def session_key(self) -> Optional[str]:
        return self.mirai_session.session_key


class MessageMixin(AriadneMixin):
    """用于发送, 撤回, 获取消息的 Mixin 类."""

    @app_ctx_manager
    async def getMessageFromId(self, messageId: int) -> MessageChain:
        result = await self.adapter.call_api(
            "messageFromId",
            CallMethod.GET,
            {"sessionKey": self.session_key, "id": messageId},
        )
        return MessageChain.parse_obj(result)

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
        with enter_message_send_context(UploadMethod.Friend):
            new_msg = message.copy()
            new_msg.prepare()
            result = await self.adapter.call_api(
                "sendFriendMessage",
                CallMethod.POST,
                {
                    "sessionKey": self.session_key,
                    "target": target.id if isinstance(target, Friend) else target,
                    "messageChain": new_msg.dict()["__root__"],
                    **(
                        {"quote": quote.id if isinstance(quote, Source) else quote}
                        if quote
                        else {}
                    ),
                },
            )
            logger.info(
                "[BOT {bot_id}] Friend({friend_id}) <- {message}".format_map(
                    {
                        "bot_id": self.mirai_session.account,
                        "friend_id": target.id
                        if isinstance(target, Friend)
                        else target,
                        "message": new_msg.asDisplay(),
                    }
                )
            )
            return BotMessage(messageId=result["messageId"])

    @app_ctx_manager
    async def sendGroupMessage(
        self,
        target: Union[Group, int],
        message: MessageChain,
        *,
        quote: Optional[Union[Source, int]] = None,
    ) -> BotMessage:
        """发送消息到群组内, 可以指定回复的消息.

        Args:
            target (Union[Group, int]): 指定的群组, 可以是群组的 ID 也可以是 Group 实例.
            message (MessageChain): 有效的, 可发送的(Sendable)消息链.
            quote (Optional[Union[Source, int]], optional): 需要回复的消息, 不要忽视我啊喂?!!, 默认为 None.

        Returns:
            BotMessage: 即当前会话账号所发出消息的元数据, 内包含有一 `messageId` 属性, 可用于回复.
        """
        with enter_message_send_context(UploadMethod.Group):
            new_msg = message.copy()
            new_msg.prepare()
            result = await self.adapter.call_api(
                "sendGroupMessage",
                CallMethod.POST,
                {
                    "sessionKey": self.session_key,
                    "target": target.id if isinstance(target, Group) else target,
                    "messageChain": new_msg.dict()["__root__"],
                    **(
                        {"quote": quote.id if isinstance(quote, Source) else quote}
                        if quote
                        else {}
                    ),
                },
            )
            logger.info(
                "[BOT {bot_id}] Group({group_id}) <- {message}".format_map(
                    {
                        "bot_id": self.mirai_session.account,
                        "group_id": target.id if isinstance(target, Group) else target,
                        "message": new_msg.asDisplay(),
                    }
                )
            )
            return BotMessage(messageId=result["messageId"])

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
                    "group": group.id if isinstance(group, Group) else group,
                    "qq": target.id if isinstance(target, Member) else target,
                    "messageChain": new_msg.dict()["__root__"],
                    **(
                        {"quote": quote.id if isinstance(quote, Source) else quote}
                        if quote
                        else {}
                    ),
                },
            )
            logger.info(
                "[BOT {bot_id}] Member({member_id}, in {group_id}) <- {message}".format_map(
                    {
                        "bot_id": self.mirai_session.account,
                        "member_id": target.id
                        if isinstance(target, Member)
                        else target,
                        "group_id": group.id if isinstance(group, Group) else group,
                        "message": new_msg.asDisplay(),
                    }
                )
            )
            return BotMessage(messageId=result["messageId"])

    @app_ctx_manager
    async def sendMessage(
        self,
        target: Union[MessageEvent, Group, Friend, Member],
        message: MessageChain,
        *,
        quote: Union[bool, int, Source] = False,
    ) -> BotMessage:
        """
        依据传入的 `target` 自动发送消息.
        请注意发送给群成员时会自动作为临时消息发送.

        Args:
            target (Union[MessageEvent, Group, Friend, Member]): 消息发送目标.
            message (MessageChain): 要发送的消息链.
            quote (Union[bool, int, Source]): 若为布尔类型, 则会尝试通过传入对象解析要回复的消息,
            否则会视为 `messageId` 处理.

        Returns:
            BotMessage: 即当前会话账号所发出消息的元数据, 内包含有一 `messageId` 属性, 可用于回复.
        """
        data = {"message": message}
        # quote
        if isinstance(quote, bool) and quote and isinstance(target, MessageEvent):
            data["quote"] = target.messageChain.getFirst(Source)
        elif isinstance(quote, (int, Source)):
            data["quote"] = quote
        # target: MessageEvent
        if isinstance(target, GroupMessage):
            data["target"] = target.sender.group
        elif isinstance(target, (FriendMessage, TempMessage)):
            data["target"] = target.sender
        else:  # target: sender
            data["target"] = target
        # send message
        if isinstance(data["target"], Friend):
            return await self.sendFriendMessage(**data)
        if isinstance(data["target"], Group):
            return await self.sendGroupMessage(**data)
        elif isinstance(data["target"], Member):
            return await self.sendTempMessage(**data)
        else:
            raise NotImplementedError(
                f"Unable to send message with {target} as target."
            )

    @app_ctx_manager
    async def sendNudge(self, target: Union[Friend, Member]) -> None:
        """
        向指定的群组成员或好友发送戳一戳消息.

        Args:
            target (Union[Friend, Member]): 发送戳一戳的目标.

        Returns:
            None: 没有返回.
        """
        await self.adapter.call_api(
            "sendNudge",
            CallMethod.POST,
            {
                "sessionKey": self.session_key,
                "target": target.id,
                "subject": target.group.id if isinstance(target, Member) else target.id,
                "kind": {Member: "Group", Friend: "Friend"}[target.__class__],
            },
        )

    @app_ctx_manager
    async def recallMessage(self, target: Union[Source, BotMessage, int]) -> None:
        """撤回特定的消息; 撤回自己的消息需要在发出后 2 分钟内才能成功撤回; 如果在群组内, 需要撤回他人的消息则需要管理员/群主权限.

        Args:
            target (Union[Source, BotMessage, int]): 特定信息的 `messageId`, 可以是 `Source` 实例, `BotMessage` 实例或者是单纯的 int 整数.

        Returns:
            None: 没有返回.
        """
        if isinstance(target, BotMessage):
            target = target.messageId
        elif isinstance(target, Source):
            target = target.id

        await self.adapter.call_api(
            "recall",
            CallMethod.POST,
            {"sessionKey": self.session_key, "target": target},
        )


class RelationshipMixin(AriadneMixin):
    """获取各种关系模型的 Mixin 类."""

    @app_ctx_manager
    async def getFriendList(self) -> List[Friend]:
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
    async def getMember(
        self, group: Union[Group, int], member_id: int
    ) -> Optional[Member]:
        """尝试从已知的群组唯一 ID 和已知的群组成员的 ID, 获取对应成员的信息; 可能返回 None.

        Args:
            group_id (Union[Group, int]): 已知的群组唯一 ID
            member_id (int): 已知的群组成员的 ID

        Returns:
            Member: 操作成功, 你得到了你应得的.
            None: 未能获取到.
        """
        data = await self.getMemberList(group)
        for i in data:
            if i.id == member_id:
                return i

    @app_ctx_manager
    async def getBotProfile(self) -> Profile:
        result = await self.adapter.call_api(
            "botProfile",
            CallMethod.GET,
            {"sessionKey": self.session_key},
        )
        return Profile.parse_obj(result)

    @app_ctx_manager
    async def getFriendProfile(self, friend: Union[Friend, int]) -> Profile:
        result = await self.adapter.call_api(
            "friendProfile",
            CallMethod.GET,
            {
                "sessionKey": self.session_key,
                "target": friend.id if isinstance(friend, Friend) else friend,
            },
        )
        return Profile.parse_obj(result)

    @app_ctx_manager
    async def getMemberProfile(
        self, member: Union[Member, int], group: Optional[Union[Group, int]] = None
    ) -> Profile:
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
    async def deleteFriend(self, target: Union[Friend, int]):
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
    async def muteMember(
        self, group: Union[Group, int], member: Union[Member, int], time: int
    ):
        """
        在指定群组禁言指定群成员; 需要具有相应权限(管理员/群主); `time` 不得大于 `30*24*60*60=2592000` 或小于 `0`, 否则会自动修正;
        当 `time` 小于等于 `0` 时, 不会触发禁言操作; 禁言对象极有可能触发 `PermissionError`, 在这之前请对其进行判断!

        Args:
            group (Union[Group, int]): 指定的群组
            member (Union[Member, int]): 指定的群成员(只能是普通群员或者是管理员, 后者则要求群主权限)
            time (int): 禁言事件, 单位秒, 修正规则: `{time|0 < time <= 2592000}`

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
    async def unmuteMember(self, group: Union[Group, int], member: Union[Member, int]):
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
    async def muteAll(self, group: Union[Group, int]):
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
    async def unmuteAll(self, group: Union[Group, int]):
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
    ):
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
    async def quitGroup(self, group: Union[Group, int]):
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
    async def setEssence(self, target: Union[Source, BotMessage, int]):
        """
        添加指定消息为群精华消息; 需要具有相应权限(管理员/群主).
        请自行判断消息来源是否为群组.

        Args:
            target (Union[Source, BotMessage, int]): 特定信息的 `messageId`, 可以是 `Source` 实例, `BotMessage` 实例或者是单纯的 int 整数.

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
    async def modifyGroupConfig(self, group: Union[Group, int], config: GroupConfig):
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

    @app_ctx_manager
    async def getMemberInfo(
        self, member: Union[Member, int], group: Optional[Union[Group, int]] = None
    ) -> MemberInfo:
        """
        获取指定群组成员的可修改状态.

        Args:
            member (Union[Member, int]): 指定群成员, 可为 Member 实例, 若前设成立, 则不需要提供 group.
            group (Optional[Union[Group, int]], optional): 如果 member 为 Member 实例, 则不需要提供本项, 否则需要. 默认为 None.

        Raises:
            TypeError: 提供了错误的参数, 阅读有关文档得到问题原因

        Returns:
            MemberInfo: 指定群组成员的可修改状态
        """
        if not group and not isinstance(member, Member):
            raise TypeError(
                "you should give a Member instance if you cannot give a Group instance to me."
            )
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

        return MemberInfo.parse_obj(result)

    @app_ctx_manager
    async def modifyMemberInfo(
        self,
        member: Union[Member, int],
        info: MemberInfo,
        group: Optional[Union[Group, int]] = None,
    ):
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
            raise TypeError(
                "you should give a Member instance if you cannot give a Group instance to me."
            )
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
    ):
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
            raise TypeError(
                "you should give a Member instance if you cannot give a Group instance to me."
            )
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


class FileMixin(AriadneMixin):
    """用于对文件进行各种操作的 Mixin 类."""

    @app_ctx_manager
    async def listFile(
        self,
        target: Union[Friend, Group, int],
        id: str = "",
        offset: Optional[int] = 0,
        size: Optional[int] = 1,
        with_download_info: bool = False,
    ) -> List[FileInfo]:
        """
        列出指定文件夹下的所有文件.

        Args:
            target (Union[Friend, Group, int]): 要列出文件的根位置,
            为群组或好友或QQ号（当前仅支持群组）
            id (str): 文件夹ID, 空串为根目录
            offset (int): 分页偏移
            size (int): 分页大小
            with_download_info (bool): 是否携带下载信息, 无必要不要携带

        Returns:
            List[FileInfo]: 返回的文件信息列表.
        """
        if isinstance(target, Friend):
            raise NotImplementedError(f"Not implemented for friend")

        target = target.id if isinstance(target, Friend) else target
        target = target.id if isinstance(target, Group) else target

        result = await self.adapter.call_api(
            "file/list",
            CallMethod.GET,
            {
                "sessionKey": self.session_key,
                "id": id,
                "target": target,
                "withDownloadInfo": str(
                    with_download_info
                ),  # yarl don't accept boolean
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
            target (Union[Friend, Group, int]): 要列出文件的根位置,
            为群组或好友或QQ号（当前仅支持群组）
            id (str): 文件ID, 空串为根目录
            with_download_info (bool): 是否携带下载信息, 无必要不要携带

        Returns:
            FileInfo: 返回的文件信息.
        """
        if isinstance(target, Friend):
            raise NotImplementedError(f"Not implemented for friend")

        target = target.id if isinstance(target, Friend) else target
        target = target.id if isinstance(target, Group) else target

        result = await self.adapter.call_api(
            "file/info",
            CallMethod.GET,
            {
                "sessionKey": self.session_key,
                "id": id,
                "target": target,
                "withDownloadInfo": str(
                    with_download_info
                ),  # yarl don't accept boolean
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
            target (Union[Friend, Group, int]): 要列出文件的根位置,
            为群组或好友或QQ号（当前仅支持群组）
            name (str): 要创建的文件夹名称.
            id (str): 上级文件夹ID, 空串为根目录

        Returns:
            FileInfo: 新创建文件夹的信息.
        """
        if isinstance(target, Friend):
            raise NotImplementedError(f"Not implemented for friend")

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
    ):
        """
        删除指定文件.

        Args:
            target (Union[Friend, Group, int]): 要列出文件的根位置,
            为群组或好友或QQ号（当前仅支持群组）
            id (str): 文件ID

        Returns:
            None: 没有返回.
        """
        if isinstance(target, Friend):
            raise NotImplementedError(f"Not implemented for friend")

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
    ):
        """
        移动指定文件.

        Args:
            target (Union[Friend, Group, int]): 要列出文件的根位置,
            为群组或好友或QQ号（当前仅支持群组）
            id (str): 源文件ID
            dest_id (str): 目标文件夹ID

        Returns:
            None: 没有返回.
        """
        if isinstance(target, Friend):
            raise NotImplementedError(f"Not implemented for friend")

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
    ):
        """
        重命名指定文件.

        Args:
            target (Union[Friend, Group, int]): 要列出文件的根位置,
            为群组或好友或QQ号（当前仅支持群组）
            id (str): 源文件ID
            dest_name (str): 目标文件新名称.

        Returns:
            None: 没有返回.
        """
        if isinstance(target, Friend):
            raise NotImplementedError(f"Not implemented for friend")

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
        data: bytes,
        method: UploadMethod,
        target: Union[Friend, Group, int],
        path: str = "",
    ) -> "FileInfo":
        """
        上传文件到指定目标, 需要提供: 文件的原始数据(bytes), 文件的上传类型,
        上传目标, (可选)上传目录ID.
        Args:
            data (bytes): 文件的原始数据
            method (UploadMethod): 文件的上传类型
        Returns:
            FileInfo: 文件信息
        """

        if method != UploadMethod.Group or isinstance(target, Friend):
            raise NotImplementedError(f"Not implemented for {method}")

        target = target.id if isinstance(target, Friend) else target
        target = target.id if isinstance(target, Group) else target

        result = await self.adapter.call_api(
            "file/upload",
            CallMethod.MULTIPART,
            {
                "sessionKey": self.session_key,
                "type": method.value,
                "target": target,
                "path": path,
                "file": data,
            },
        )

        return FileInfo.parse_obj(result)


class MultimediaMixin(AriadneMixin):
    """用于与多媒体信息交互的 Mixin 类."""

    @app_ctx_manager
    async def uploadImage(self, data: bytes, method: UploadMethod) -> "Image":
        """上传一张图片到远端服务器, 需要提供: 图片的原始数据(bytes), 图片的上传类型.
        Args:
            image_bytes (bytes): 图片的原始数据
            method (UploadMethod): 图片的上传类型
        Returns:
            Image: 生成的图片消息元素
        """
        from .message.element import Image

        result = await self.adapter.call_api(
            "uploadImage",
            CallMethod.MULTIPART,
            {
                "sessionKey": self.session_key,
                "type": method.value,
                "img": data,
            },
        )

        return Image.parse_obj(result)

    @app_ctx_manager
    async def uploadVoice(self, data: bytes, method: UploadMethod) -> "Voice":
        """上传语音到远端服务器, 需要提供: 语音的原始数据(bytes), 语音的上传类型.
        Args:
            data (bytes): 语音的原始数据
            method (UploadMethod): 语音的上传类型
        Returns:
            Voice: 生成的语音消息元素
        """
        from .message.element import Voice

        result = await self.adapter.call_api(
            "uploadVoice",
            CallMethod.MULTIPART,
            {
                "sessionKey": self.session_key,
                "type": method.value,
                "voice": data,
            },
        )

        return Voice.parse_obj(result)


class Ariadne(
    MessageMixin, RelationshipMixin, OperationMixin, FileMixin, MultimediaMixin
):
    """
    艾莉亚德妮 (Ariadne).

    面向 `mirai-api-http` 接口的实际功能实现.

    你的应用大多都围绕着本类及本类的实例展开.

    Attributes:
        broadcast (Broadcast): 被指定的, 外置的事件系统, 即 `Broadcast Control`,
            通常你不需要干涉该属性;
        adapter (Adapter): 后端适配器, 负责实际与 `mirai-api-http` 进行交互.
    """

    def __init__(
        self,
        broadcast: Broadcast,
        adapter: Adapter,
        *,
        chat_log_config: Optional[Union[ChatLogConfig, Literal[False]]] = None,
        use_loguru_traceback: Optional[bool] = True,
        use_bypass_listener: Optional[bool] = False,
    ):
        """
        初始化 Ariadne.

        Args:
            broadcast (Broadcast): 被指定的, 外置的事件系统, 即 `Broadcast Control` 实例.
            adapter (Adapter): 后端适配器, 负责实际与 `mirai-api-http` 进行交互.
            chat_log_config (ChatLogConfig or Literal[False]): 聊天日志的配置, 请移步 `ChatLogConfig` 查看使用方法. 设置为 False 则会完全禁用聊天日志.
            use_loguru_traceback (bool): 是否注入 loguru 以获得对 traceback.print_exception() 与 sys.excepthook 的完全控制.
            use_bypass_listener (bool): 是否注入 BypassListener 以获得子事件监听支持
        """
        self.broadcast: Broadcast = broadcast
        if use_bypass_listener:
            inject_bypass_listener(self.broadcast)
        self.adapter: Adapter = adapter
        self.adapter.app = self
        self.mirai_session: MiraiSession = adapter.mirai_session
        self.loop: AbstractEventLoop = broadcast.loop
        self.daemon_task: Optional[Task] = None
        self.running: bool = False
        self.remote_version: str = ""
        chat_log_enabled = True if chat_log_config is not False else False
        self.chat_log_cfg: ChatLogConfig = (
            chat_log_config
            if chat_log_config
            else ChatLogConfig(enabled=chat_log_enabled)
        )
        if use_loguru_traceback:
            inject_loguru_traceback()

    @classmethod
    def create(
        cls,
        *,
        session: MiraiSession,
        broadcast: Optional[Broadcast] = None,
        loop: Optional[AbstractEventLoop] = None,
    ) -> "Ariadne":
        """快速创建一个 `Ariadne` 实例.

        Args:
            session (MiraiSession): 连接信息, 如账号和 verifyKey 等.
            broadcast (Optional[Broadcast]): 被指定的, 外置的事件系统, 即 `Broadcast Control` 实例.
            loop (Optional[AbstractEventLoop]): 事件循环实例.

        Returns:
            Ariadne: 创建的实例.
        """
        if not loop:
            loop = asyncio.new_event_loop()
        if not broadcast:
            broadcast = Broadcast(loop=loop)
        adapter = DefaultAdapter(broadcast=broadcast, mirai_session=session)
        return cls(broadcast, adapter)

    async def daemon(self, retry_interval: float = 5.0):
        logger.debug("Application daemon started.")
        while self.running:
            try:
                await self.adapter.start()
                self.broadcast.postEvent(AdapterLaunched(self))
                try:
                    if self.adapter.fetch_task:
                        await self.adapter.fetch_task
                except Exception as e:
                    logger.exception(e)
                await self.adapter.stop()
                self.broadcast.postEvent(AdapterShutdowned(self))
                logger.warning(f"daemon: adapter down, restart in {retry_interval}s")
                await asyncio.sleep(retry_interval)
                logger.info("daemon: restarting adapter")
            except CancelledError:
                await self.adapter.stop()
        logger.debug("Application daemon stopped.")

    async def launch(self):
        if not self.running:
            self.running = True
            start_time = time.time()
            logger.info("Launching app...")
            self.broadcast.dispatcher_interface.inject_global_raw(
                ApplicationMiddlewareDispatcher(self)
            )
            if self.chat_log_cfg.enabled:
                self.chat_log_cfg.initialize(self)
            self.daemon_task = self.loop.create_task(self.daemon())
            while not self.adapter.session_activated:
                await asyncio.sleep(0.001)
            self.broadcast.postEvent(ApplicationLaunched(self))
            self.remote_version = await self.getVersion()
            logger.info(f"Remote version: {self.remote_version}")
            logger.info(f"Application launched with {time.time() - start_time:.2}s")

    async def stop(self):
        if self.running:
            self.broadcast.postEvent(ApplicationShutdowned(self))
            self.running = False
            if self.daemon_task:
                self.daemon_task.cancel()
                self.daemon_task = None
            await self.adapter.stop()
            for t in asyncio.all_tasks(self.loop):
                if t is not asyncio.current_task(self.loop):
                    t.cancel()
                    try:
                        await t
                    except asyncio.CancelledError:
                        pass

    async def lifecycle(self):
        await self.launch()
        try:
            if self.daemon_task:
                await self.daemon_task
        except CancelledError:
            pass
        await self.stop()

    @app_ctx_manager
    async def getVersion(self, auto_set: bool = True):
        if self.mirai_session.version:
            return self.mirai_session.version
        result = await self.adapter.call_api.__wrapped__(
            self.adapter, "about", CallMethod.GET
        )
        version = result["version"]
        if auto_set:
            self.mirai_session.version = version
        return version

    async def __aenter__(self) -> "Ariadne":
        await self.launch()

        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            await self.stop()
        except:
            pass

        if tb is not None:
            raise exc
