import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))

from graia.broadcast import Broadcast
from loguru import logger

from graia.ariadne.adapter import CombinedAdapter
from graia.ariadne.model import MiraiSession

if __name__ == "__main__":
    url = input()
    account = input()
    verify_key = input()

    loop = asyncio.new_event_loop()
    bcc = Broadcast(loop=loop)
    adapter = CombinedAdapter(bcc, MiraiSession(url, account, verify_key))

    async def resp():
        async for msg in adapter.fetch_cycle():
            logger.info(f"received: {msg}")

    try:
        loop.run_until_complete(resp())
    except KeyboardInterrupt:
        adapter.stop()
