import asyncio

from graia.broadcast import Broadcast

from graia.ariadne import AriadneMiraiApplication
from graia.ariadne.adapter import DefaultAdapter
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend, MiraiSession

loop = asyncio.new_event_loop()

bcc = Broadcast(loop=loop)
app = AriadneMiraiApplication(
    broadcast=bcc,
    adapter=DefaultAdapter(
        bcc,
        MiraiSession(
            host="http://localhost:8080",  # 填入 httpapi 服务运行的地址
            verify_key="ServiceVerifyKey",  # 填入 verifyKey
            account=123456789,  # 你的机器人的 qq 号
        ),
    ),
)


@bcc.receiver("FriendMessage")
async def friend_message_listener(app: AriadneMiraiApplication, friend: Friend):
    await app.send_message(friend, MessageChain.create([Plain("Hello, World!")]))


loop.run_until_complete(app.lifecycle())
