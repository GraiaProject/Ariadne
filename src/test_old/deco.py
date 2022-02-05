import asyncio

from graia.broadcast import Broadcast

from graia.ariadne.entry import *
from graia.ariadne.entry.event import *
from graia.ariadne.entry.message import *

a = Ariadne(MiraiSession("https://0.0.0.0", 12345, "test"))


@a.broadcast.receiver(GroupMessage)
async def g(c: MessageChain = DetectSuffix("test")):
    print(c)


async def main():
    ev = GroupMessage(
        messageChain=MessageChain.create(Plain("hello test")),
        sender=Member(
            id=123,
            memberName="test",
            permission=MemberPerm.Member,
            group=Group(id=123, name="test", permission=MemberPerm.Member),
        ),
    )
    listeners = list(a.broadcast.default_listener_generator(ev.__class__))
    for _ in range(5):
        print("Before broadcast: ", listeners[0].oplog)
        await a.broadcast.layered_scheduler(listeners, ev)
        print("After broadcast: ", listeners[0].oplog)


asyncio.run(main())
