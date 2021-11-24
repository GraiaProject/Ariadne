import os
import sys
sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))
from graia.broadcast import Broadcast
from graia.saya import Channel, Saya
from graia.saya.event import SayaModuleInstalled
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage, GroupMessage, Group, Member
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.model import Friend, MiraiSession
from loguru import logger

saya = Saya.current()
channel = Channel.current()

@channel.use(ListenerSchema(
    listening_events=[SayaModuleInstalled]
))
async def module_listener(event: SayaModuleInstalled):
    logger.info(f"{event.module}::模块加载成功!!!")
