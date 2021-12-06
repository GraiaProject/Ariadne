import asyncio
import os

from graia.broadcast import Broadcast
from loguru import logger

from graia.ariadne.adapter import DebugAdapter
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage, GroupMessage, MessageEvent
from graia.ariadne.event.mirai import GroupRecallEvent, NewFriendRequestEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain
from graia.ariadne.message.parser.pattern import FullMatch, RegexMatch, WildcardMatch
from graia.ariadne.message.parser.twilight import Sparkle, Twilight
from graia.ariadne.model import Friend, Group, Member, MiraiSession

if __name__ == "__main__":
    url, account, verify_key = open(os.path.join(__file__, "..", "test.temp"), "r").read().split(" ")
    ALL_FLAG = False
    loop = asyncio.new_event_loop()
    loop.set_debug(True)

    bcc = Broadcast(loop=loop)

    app = Ariadne(
        DebugAdapter(bcc, MiraiSession(url, account, verify_key)),
        loop=loop,
        use_bypass_listener=True,
        max_retry=5,
        await_task=True,
    )

    bcc = app.create(Broadcast)

    @bcc.receiver(FriendMessage)
    async def send(app: Ariadne, chain: MessageChain, friend: Friend):
        if chain.asDisplay().startswith(".wait"):
            await app.sendFriendMessage(friend, MessageChain.create("Wait for 5s!"))
            await asyncio.sleep(5.0)
            await app.sendFriendMessage(friend, MessageChain.create("Complete!"))

    @bcc.receiver(
        MessageEvent, dispatchers=[Twilight(Sparkle([FullMatch(".test")], {"arg": WildcardMatch()}))]
    )
    async def reply1(app: Ariadne, event: MessageEvent, arg: WildcardMatch):
        await app.sendMessage(event, MessageChain.create("Auto reply to ") + arg.result)

    @bcc.receiver(NewFriendRequestEvent)
    async def accept(event: NewFriendRequestEvent):
        await event.accept("Welcome!")

    @bcc.receiver(MessageEvent, dispatchers=[Twilight(Sparkle([FullMatch(".test")]))])
    async def reply2(app: Ariadne, event: MessageEvent):
        await app.sendMessage(event, MessageChain.create("Auto reply to /test!"))

    @bcc.receiver(GroupMessage)
    async def reply3(app: Ariadne, chain: MessageChain, group: Group, member: Member):
        if "Hi!" in chain and chain.has(At):
            await app.sendGroupMessage(
                group,
                MessageChain.create([At(chain.getFirst(At).target), Plain("Hello World!")]),
            )  # WARNING: May raise UnknownTarget

    @bcc.receiver(GroupRecallEvent)
    async def anti_recall(app: Ariadne, event: GroupRecallEvent):
        msg = await app.getMessageFromId(event.messageId)
        await app.sendGroupMessage(event.group, msg.messageChain)

    @bcc.receiver(
        FriendMessage,
        dispatchers=[Twilight(Sparkle([RegexMatch("[./]stop")]))],
    )
    async def stop(app: Ariadne):
        await app.request_stop()

    async def main():
        await app.launch()
        logger.debug(await app.getVersion())
        logger.debug(await app.getBotProfile())
        if ALL_FLAG:
            group_list = await app.getGroupList()
            logger.debug(group_list)
            friend_list = await app.getFriendList()
            logger.debug(friend_list)
            member_list = await app.getMemberList(group_list[0])
            logger.debug(member_list)
            logger.debug(await app.getFriendProfile(friend_list[0]))
            logger.debug(await app.getMemberProfile(member_list[0], group_list[0]))
            logger.debug(await app.getMemberProfile(member_list[0]))
        await app.lifecycle()


try:
    loop.run_until_complete(main())
    loop.run_until_complete(main())
except KeyboardInterrupt:
    loop.run_until_complete(app.wait_for_stop())
