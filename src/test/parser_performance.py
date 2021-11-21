import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))

import time

from devtools import debug

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain
from graia.ariadne.message.parser.literature import Literature
from graia.ariadne.message.parser.pattern import (
    ArgumentMatch,
    BoxParameter,
    FullMatch,
    ParamPattern,
    WildcardMatch,
)
from graia.ariadne.message.parser.twilight import Sparkle, Twilight

RUN = 2000

if __name__ == "__main__":
    print("Run 1:")
    li = Literature(".test", arguments={"f": BoxParameter(["foo"])})
    twi = Twilight(Sparkle([FullMatch(".test")], {"foo": ArgumentMatch("--foo", "-f")}))
    msg = MessageChain.create(".test", " --foo ", At(123))
    debug(li.parse_message(li.prefix_match(msg)))
    st = time.time()
    for _ in range(RUN):
        li.parse_message(li.prefix_match(msg))
    ed = time.time()

    print(f"Literature: {RUN / (ed-st):.2f}msg/s")

    debug(twi.gen_sparkle(msg))

    st = time.time()
    for _ in range(RUN):
        twi.gen_sparkle(msg)
    ed = time.time()

    print(f"Twilight: {RUN / (ed-st):.2f}msg/s")

    print("Run 2:")

    twi = Twilight(Sparkle([FullMatch(".test"), WildcardMatch()]))
    debug(li.parse_message(li.prefix_match(msg)))
    st = time.time()
    for _ in range(RUN):
        li.parse_message(li.prefix_match(msg))
    ed = time.time()

    print(f"Literature: {RUN / (ed-st):.2f}msg/s")

    debug(twi.gen_sparkle(msg))

    st = time.time()
    for _ in range(RUN):
        twi.gen_sparkle(msg)
    ed = time.time()

    print(f"Twilight: {RUN / (ed-st):.2f}msg/s")
