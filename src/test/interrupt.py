import asyncio
import os

from graia.broadcast.interrupt import InterruptControl
from graia.broadcast.interrupt.waiter import Waiter

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend, MiraiSession

url, account, verify_key = open(os.path.join(__file__, "..", "test.temp"), "r").read().split(" ")
app = Ariadne(MiraiSession(host=url, verify_key=verify_key, account=account))
inc = app.create(InterruptControl)


@app.broadcast.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne, friend: Friend):
    @Waiter.create_using_function([FriendMessage])
    async def waiter1(waiter1_friend: Friend, waiter1_event: FriendMessage, waiter1_message: MessageChain):
        if waiter1_friend.id == friend.id:
            waiter1_saying = waiter1_message.asDisplay()
            if waiter1_saying == "取消":
                return False
            elif waiter1_saying == "run":
                return waiter1_event

    try:
        await asyncio.wait_for(inc.wait(waiter1), timeout=30)
    except asyncio.TimeoutError:
        await app.sendMessage(friend, MessageChain.create([Plain("Time Out!")]))

    await app.sendMessage(friend, MessageChain.create([Plain("Hello, World!")]))


app.launch_blocking()
