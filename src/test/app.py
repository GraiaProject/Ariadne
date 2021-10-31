import asyncio
import os
import sys

from graia.broadcast.interfaces.dispatcher import DispatcherInterface

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))


from graia.broadcast import Broadcast
from loguru import logger

from graia.ariadne.adapter import DebugAdapter
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage, MessageEvent
from graia.ariadne.event.mirai import NewFriendRequestEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.model import Friend, MiraiSession

if __name__ == "__main__":
    url, account, verify_key = (
        open(os.path.join(__file__, "..", "test.temp"), "r").read().split(" ")
    )
    ALL_FLAG = True
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    bcc = Broadcast(loop=loop)
    adapter = DebugAdapter(bcc, MiraiSession(url, account, verify_key))
    app = Ariadne(bcc, adapter, use_bypass_listener=True)

    @bcc.receiver(FriendMessage)
    async def reply(app: Ariadne, chain: MessageChain, friend: Friend):
        await app.sendFriendMessage(friend, MessageChain.create("Hello, World!"))

    @bcc.receiver(MessageEvent)
    async def _(app: Ariadne, dii: DispatcherInterface):
        await app.sendMessage(dii.event, MessageChain.create("Auto reply!"))

    @bcc.receiver(NewFriendRequestEvent)
    async def _(event: NewFriendRequestEvent):
        await event.accept("Welcome!")

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
    except KeyboardInterrupt:
        loop.run_until_complete(app.stop())
