import os
import sys

from prompt_toolkit.styles.style import Style

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))
import asyncio
from datetime import datetime

from graia.broadcast import Broadcast
from graia.saya import Saya
from graia.saya.builtins.broadcast.behaviour import BroadcastBehaviour
from graia.scheduler import GraiaScheduler
from graia.scheduler.saya.behaviour import GraiaSchedulerBehaviour
from loguru import logger

from graia.ariadne.adapter import DebugAdapter
from graia.ariadne.app import Ariadne
from graia.ariadne.console import Console
from graia.ariadne.console.saya import ConsoleBehaviour
from graia.ariadne.event.message import FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.model import Friend, MiraiSession

if __name__ == "__main__":
    url, account, verify_key, *_ = open(os.path.join(__file__, "..", "test.temp"), "r").read().split(" ")
    ALL_FLAG = True
    loop = asyncio.new_event_loop()
    bcc = Broadcast(loop=loop)
    saya = Saya(bcc)
    adapter = DebugAdapter(bcc, MiraiSession(url, account, verify_key))
    console = Console(
        bcc,
        r_prompt="<{current_time}>",
        style=Style.from_dict(
            {
                "rprompt": "bg:#00ffff #ffffff",
            }
        ),
        extra_data_getter=[lambda: {"current_time": datetime.now().time().isoformat()}],
    )

    app = Ariadne(adapter, broadcast=bcc)

    saya.install_behaviours(
        BroadcastBehaviour(bcc), ConsoleBehaviour(console), GraiaSchedulerBehaviour(GraiaScheduler(loop, bcc))
    )

    console.start()

    with saya.module_context():
        saya.require("saya_test_downstream")

    app.launch_blocking()
