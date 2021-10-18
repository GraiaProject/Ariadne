import asyncio
import getopt
import itertools
import os
import re
import shlex
import sys
from typing import Dict, List, Tuple

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))

from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.signatures import Force
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.utilles import printer
from loguru import logger

from graia.ariadne.message.chain import MessageChain, MessageIndex
from graia.ariadne.message.element import (
    App,
    At,
    Element,
    FlashImage,
    Json,
    Plain,
    Poke,
    Quote,
    Source,
    Voice,
    Xml,
)
from graia.ariadne.message.parser.literature import Literature
from graia.ariadne.message.parser.pattern import (
    BoxParameter,
    ParamPattern,
    SwitchParameter,
)

if __name__ == "__main__":
    from graia.ariadne.message.element import At, AtAll

    mc = MessageChain.create(
        [
            Plain('test n --f3 "1 2 tsthd thsd ydj re7u  '),
            At(12345678),
            Plain(' " --f34 "arg arega er ae aghr ae rtyh'),
            At(876554321),
            Plain(' "'),
        ]
    )

    l = Literature(
        "test",
        "n",
        arguments={
            "a": BoxParameter(["test_f1", "f3"], "f"),
            "b": SwitchParameter(["f34"], "d"),
        },
    )
    from devtools import debug

    debug(l.prefix_match(mc))
    debug(l.parse_message(l.prefix_match(mc)))
    print(mc.asDisplay())
