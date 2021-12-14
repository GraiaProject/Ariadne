import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))
import asyncio

from graia.broadcast import Broadcast
from graia.saya import Channel, Saya
from graia.saya.builtins.broadcast import ListenerSchema

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.model import Friend, MiraiSession

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema([FriendMessage]))
async def reply(app: Ariadne, chain: MessageChain, friend: Friend):
    await app.sendFriendMessage(friend, MessageChain.create("Hello, World!"))
