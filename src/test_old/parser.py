import asyncio

import devtools
from graia.broadcast import Broadcast

from graia.ariadne.event.message import MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import *
from graia.ariadne.message.parser.base import *
from graia.ariadne.message.parser.twilight import *
from graia.ariadne.model import Friend

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    bcc = Broadcast(loop=loop)

    @bcc.receiver(MessageEvent)
    async def pup(
        result: MessageChain = Compose(DetectPrefix(".test"), DetectPrefix("option"), DetectPrefix("end")),
    ):
        devtools.debug(result)

    @bcc.receiver(MessageEvent)
    async def pap(result: MessageChain = Mention(".test")):
        devtools.debug(result)

    @bcc.receiver(MessageEvent, decorators=[DetectPrefix(".system")])
    async def trigger(result: MessageChain):
        print("Triggered:")
        devtools.debug(result)

    @bcc.receiver(MessageEvent, dispatchers=[Twilight(FullMatch(".twilight"), ElementMatch(At) @ "elem")])
    async def print_elem(elem: ElementResult):
        print("Element: ", elem)

    async def main():
        bcc.postEvent(
            MessageEvent(
                messageChain=MessageChain.create(".test option end"),
                sender=Friend(id=123, nickname="opq", remark="test"),
            )
        )
        bcc.postEvent(
            MessageEvent(
                messageChain=MessageChain.create(".system abstract"),
                sender=Friend(id=123, nickname="opq", remark="test"),
            )
        )
        bcc.postEvent(
            MessageEvent(
                messageChain=MessageChain.create(".twilight ", At(123)),
                sender=Friend(id=123, nickname="opq", remark="test"),
            )
        )
        await asyncio.sleep(0.2)

    loop.run_until_complete(main())
