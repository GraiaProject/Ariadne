import asyncio
import os

from fastapi import FastAPI
from graia.broadcast import Broadcast
from loguru import logger
from uvicorn import Config

from graia.ariadne.adapter.reverse import ReverseWebsocketAdapter
from graia.ariadne.model import MiraiSession

if __name__ == "__main__":
    url, account, verify_key, target, t_group = (
        open(os.path.join(__file__, "..", "test.temp"), "r").read().split(" ")
    )
    loop = asyncio.new_event_loop()
    bcc = Broadcast(loop=loop)
    adapter = ReverseWebsocketAdapter(bcc, MiraiSession("/ws", account, verify_key), port=21444)
    try:
        loop.run_until_complete(adapter.start())
        loop.run_until_complete(adapter.fetch_task)
    except KeyboardInterrupt:
        loop.run_until_complete(adapter.stop())
