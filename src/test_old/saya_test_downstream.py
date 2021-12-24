import asyncio
import os

from graia.broadcast import Broadcast
from graia.saya import Channel, Saya
from graia.saya.builtins.broadcast import ListenerSchema
from graia.scheduler.saya.schema import SchedulerSchema
from graia.scheduler.timers import every_custom_seconds
from loguru import logger
from prompt_toolkit.styles.style import Style

from graia.ariadne.app import Ariadne
from graia.ariadne.console import Console
from graia.ariadne.console.saya import ConsoleSchema
from graia.ariadne.event.lifecycle import ApplicationShutdowned
from graia.ariadne.event.message import FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.parser.twilight import ParamMatch, Sparkle, Twilight
from graia.ariadne.model import Friend, MiraiSession

saya = Saya.current()
channel = Channel.current()


@channel.use(ListenerSchema([FriendMessage]))
async def reply(app: Ariadne, chain: MessageChain, friend: Friend):
    await app.sendFriendMessage(friend, MessageChain.create("Hello, World!"))


@channel.use(ConsoleSchema([Twilight.from_command("permission set {0} {1}")]))
async def display(sparkle: Sparkle):
    logger.info(f"Set {sparkle[ParamMatch, 0].result}'s permission to {sparkle[ParamMatch, 1].result}")


@channel.use(ListenerSchema([ApplicationShutdowned]))
async def info(app: Ariadne):
    logger.info("Stopped!")
    await app.sendFriendMessage(
        open(os.path.join(__file__, "..", "test.temp"), "r").read().split()[3], MessageChain(["Shut down."])
    )


@channel.use(SchedulerSchema(every_custom_seconds(10)))
async def send(app: Ariadne):
    logger.info("OK")


@channel.use(ConsoleSchema([Twilight.from_command(".stop")]))
async def stop(app: Ariadne, console: Console):

    res: str = await console.prompt(
        [("class:fg", "Are you sure to stop?")],
        "<y/n>",
        Style.from_dict({"fg": "#ff0000", "rprompt": "bg:#00ffff #ffffff"}),
    )

    if res.lower().startswith("y"):
        await app.stop()
        console.stop()
