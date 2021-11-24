import asyncio,os
from graia.broadcast import Broadcast
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend, MiraiSession
from graia.ariadne.event.message import FriendMessage
from graia.broadcast import Broadcast

loop = asyncio.get_event_loop()
bcc = Broadcast(loop = loop)
miraisession = MiraiSession(host="http://localhost:8888", account=12345678, verify_key="12345678")

app = Ariadne(
    connect_info=miraisession,
    loop=loop,
    broadcast=bcc,
    )

@bcc.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne, friend: Friend):
    await app.sendMessage(friend, MessageChain.create([Plain("Hello, World!")]))

if __name__ == "__main__":
    app.run(reload=True)








