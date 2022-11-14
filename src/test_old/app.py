import asyncio
import os
import re
import sys
from datetime import datetime
from typing import Annotated, Optional, Union

import creart
import devtools
from graia.amnesia.builtins.aiohttp import AiohttpServerService
from graia.saya.context import channel_instance
from loguru import logger

from graia.ariadne.connection import ConnectionInterface
from graia.ariadne.entry import *
from graia.ariadne.message.exp import MessageChain as ExpMessageChain
from graia.ariadne.message.parser.base import RegexGroup, StartsWith
from graia.ariadne.util import RichLogInstallOptions

if __name__ == "__main__":
    url, account, verify_key, target, t_group = (
        open(os.path.join(__file__, "..", "test.temp"), "r").read().split(" ")
    )
    account = int(account)
    target = int(target)
    t_group = int(t_group)
    ALL_FLAG = True
    Ariadne.config(inject_bypass_listener=True)

    app = Ariadne(
        config(
            int(account),
            verify_key,
        )
    )

    Ariadne.service.loop.set_debug(True)

    bcc = Ariadne.broadcast

    sy = app.create(Saya)
    sched = app.create(GraiaScheduler)

    channel = sy.create_main_channel()
    channel_instance.set(channel)

    @listen(GroupMessage)
    @decorate("la", DetectPrefix("high-level"))
    async def test_pref(target: Group, la: MessageChain):
        await app.send_group_message(target, la)

    with sy.behaviour_interface.require_context("__main__") as interface:
        for cube in channel.content:
            interface.allocate_cube(cube)

    @sched.schedule(every_custom_seconds(30))
    async def print_ver(app: Ariadne):
        logger.debug(await app.get_version())

    async def chk(msg: MessageChain):
        return msg.display.endswith("override")

    @bcc.receiver(CommandExecutedEvent)
    async def print_remote_cmd(event: CommandExecutedEvent):
        logger.debug(event)

    @bcc.receiver(
        MessageEvent,
        dispatchers=[CoolDown(5, override_condition=chk, stop_on_cooldown=True)],
        decorators=[DetectPrefix("trigger_wait")],
    )
    async def hdlr(
        ev: MessageEvent,
        res_time: Optional[float],
        app: Ariadne,
        sender: Union[Friend, Member],
    ):
        await app.send_message(
            ev,
            MessageChain(
                [f"""rest: {res_time}s, from {getattr(sender, "name", getattr(sender, "nickname", None))}"""]
            ),
        )

    @bcc.receiver(MessageEvent)
    async def send(app: Ariadne, ev: MessageEvent, chain: MessageChain = MentionMe()):
        logger.debug(repr(chain))
        if chain.display.startswith(".wait"):
            await app.send_message(ev, MessageChain("Wait for 5s!"))
            await asyncio.sleep(5.0)
            await app.send_message(ev, MessageChain("Complete!"))

    @bcc.receiver(MessageEvent)
    async def check_multi(chain: MessageChain):
        if chain.has(MultimediaElement):
            elem = chain.get_first(MultimediaElement)
            logger.info(elem.dict())

    @bcc.receiver(GroupEvent)
    async def log(group: Group):
        logger.info(repr(group))

    @bcc.receiver(
        GroupMessage, decorators=[CertainGroup(int(t_group))], dispatchers=[FuzzyDispatcher("github")]
    )
    async def reply_to_me(app: Ariadne, ev: MessageEvent, rate: float):
        await app.send_message(ev, MessageChain(f"Git host! rate: {rate}"))

    @bcc.receiver(
        GroupMessage, decorators=[CertainGroup(int(t_group))], dispatchers=[FuzzyDispatcher("gayhub")]
    )
    async def reply_to_me(app: Ariadne, ev: MessageEvent, rate: float):
        await app.send_message(ev, MessageChain(f"Gay host! rate: {rate}"))

    @bcc.receiver(ExceptionThrowed)
    async def e(app: Ariadne, e: ExceptionThrowed):
        await app.send_message(e.event, MessageChain(f"{e.exception}"))

    @bcc.receiver(MessageEvent, decorators=[MatchContent("!raise")])
    async def raise_(app: Ariadne, ev: MessageEvent):
        await app.send_message(ev, MessageChain("Raise!"))
        raise ValueError("Raised!")

    @bcc.receiver(
        MessageEvent,
        dispatchers=[
            Twilight(
                [
                    FullMatch(".test"),
                    "help" @ ArgumentMatch("--help", "-h", action="store_true"),
                    "arg" @ WildcardMatch().flags(re.DOTALL),
                    "verbose" @ ArgumentMatch("--verbose", action="store_true"),
                ]
            )
        ],
    )
    async def reply1(
        app: Ariadne,
        event: MessageEvent,
        arg: RegexResult,
        help: ArgResult,
        twilight: Twilight,
        verbose: ArgResult,
    ):
        if arg.result.display == "cpu":
            await app.send_message(event, MessageChain(f"{await pr()}"))
        if help.matched:
            return await app.send_message(event, MessageChain(twilight.get_help(description="Foo help!")))
        if verbose.matched:
            await app.send_message(event, MessageChain("Auto reply to \n") + arg.result)
        else:
            await app.send_message(event, MessageChain("Result: ") + arg.result)

    @bcc.receiver(NewFriendRequestEvent)
    async def accept(event: NewFriendRequestEvent):
        await event.accept("Welcome!")

    @bcc.receiver(
        MessageEvent,
        dispatchers=[
            Twilight(
                [FullMatch(".avatar")],
                preprocessor=Annotated[MessageChain, MentionMe()],
            )
        ],
    )
    async def reply2(app: Ariadne, event: MessageEvent):
        await app.send_message(event, Image(data_bytes=await event.sender.get_avatar()))

    @bcc.receiver(
        MessageEvent,
    )
    async def reply2(
        app: Ariadne, event: MessageEvent, chain: Annotated[MessageChain, DetectPrefix(".forward")]
    ):
        await app.send_message(
            event,
            Forward(ForwardNode(event.sender, datetime.now(), chain)),
        )

    @bcc.receiver(GroupMessage)
    async def reply3(app: Ariadne, chain: MessageChain, group: Group, member: Member):
        if "Hi!" in chain and chain.has(At):
            await app.send_group_message(
                group,
                MessageChain([At(chain.get_first(At).target), Plain("Hello World!")]),
            )  # WARNING: May raise UnknownTarget

    @bcc.receiver(
        FriendMessage,
        dispatchers=[Twilight([RegexMatch("[./]stop")])],
    )
    async def stop(app: Ariadne):
        app.stop()

    @bcc.receiver(
        FriendMessage,
        dispatchers=[MatchRegex("[./]regex (?P<args>.+)")],
    )
    async def regex(app: Ariadne, chain: Annotated[MessageChain, RegexGroup("args")]):
        await app.send_friend_message(target, chain)

    @bcc.receiver(GroupMessage, decorators=[StartsWith(".test exp")])
    async def exp(app: Ariadne, ev: GroupMessage, exp_c: ExpMessageChain, interf: ConnectionInterface):
        await app.send_message(ev, repr(exp_c.content))
        res = await app.send_message(ev, repr(ev))
        await app.send_message(ev, [repr(res), repr(interf)])

    @bcc.receiver(ApplicationLaunch)
    async def m(app: Ariadne):
        await app.send_friend_message(target, MessageChain("Launched!"))

    @bcc.receiver(ApplicationShutdown)
    async def m(app: Ariadne):
        await app.send_friend_message(target, MessageChain("Shutdown!"))

    @bcc.receiver(CommandExecutedEvent)
    async def cmd_log(event: CommandExecutedEvent):
        devtools.debug(event)

    @bcc.receiver(ApplicationLaunch)
    async def main():
        logger.debug(await app.get_version())
        logger.debug(await app.get_bot_profile())
        if ALL_FLAG:
            group_list = await app.get_group_list()
            await app.register_command("graia_cmd", ["graiax", "gx"], "graia_cmd <a> <b> <c>", "Test graia")
            logger.debug(group_list)
            friend_list = await app.get_friend_list()
            logger.debug(friend_list)
            member_list = await app.get_member_list(group_list[0])
            logger.debug(member_list)
            logger.debug(await app.get_friend_profile(friend_list[0]))
            logger.debug(await app.get_member_profile(member_list[0], group_list[0]))
            logger.debug(await app.get_member_profile(member_list[0]))

    Ariadne.launch_blocking()
