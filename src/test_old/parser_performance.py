import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))

import time

from devtools import debug

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At
from graia.ariadne.message.parser.twilight import ArgumentMatch, FullMatch, Twilight, WildcardMatch

RUN = 20000

if __name__ == "__main__":
    twi = Twilight([FullMatch(".test"), "foo" @ ArgumentMatch("--foo", "-f")])
    msg = MessageChain(".test", " --foo ", At(123))

    debug(twi.generate(msg))
    st = time.time()
    for _ in range(RUN):
        twi.generate(msg)
    ed = time.time()



    twi = Twilight([FullMatch(".test"), WildcardMatch()])

    debug(twi.generate(msg))

    debug(twi.generate(msg))

    st = time.time()
    for _ in range(RUN):
        twi.generate(msg)
    ed = time.time()
