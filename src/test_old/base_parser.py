import asyncio

import devtools
from graia.broadcast import Broadcast
from loguru import logger

from graia.ariadne.event.message import MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import *
from graia.ariadne.message.parser.base import *
from graia.ariadne.model import Friend

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    bcc = Broadcast(loop=loop)

    @bcc.receiver(MessageEvent)
    async def pup(result: MessageChain = DetectPrefix(".test")):
        devtools.debug(result)

    @bcc.receiver(MessageEvent)
    async def pap(result: MessageChain = Mention(".test")):
        devtools.debug(result)

    @bcc.receiver(MessageEvent, decorators=[DetectPrefix(".system")])
    async def trigger(result: MessageChain):
        print("Triggered:")
        devtools.debug(result)

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
        await asyncio.sleep(0.2)

    loop.run_until_complete(main())
