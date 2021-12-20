import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))
import asyncio

from graia.broadcast import Broadcast
from graia.saya import Saya
from graia.saya.builtins.broadcast.behaviour import BroadcastBehaviour

from graia.ariadne.adapter import DebugAdapter
from graia.ariadne.app import Ariadne
from graia.ariadne.console import Console
from graia.ariadne.console.saya import ConsoleBehaviour
from graia.ariadne.event.message import FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.model import Friend, MiraiSession

if __name__ == "__main__":
    url, account, verify_key = open(os.path.join(__file__, "..", "test.temp"), "r").read().split(" ")
    ALL_FLAG = True
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    bcc = Broadcast(loop=loop)
    saya = Saya(bcc)
    adapter = DebugAdapter(bcc, MiraiSession(url, account, verify_key))
    console = Console(bcc)

    app = Ariadne(adapter, broadcast=bcc)

    saya.install_behaviours(BroadcastBehaviour(bcc), ConsoleBehaviour(console))

    console.start()

    with saya.module_context():
        saya.require("saya_test_downstream")

    loop.run_until_complete(app.lifecycle())
    console.stop()
