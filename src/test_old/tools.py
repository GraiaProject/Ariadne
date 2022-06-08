import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))

from devtools import debug

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain
from graia.ariadne.message.formatter import Formatter

debug(
    Formatter("{name} {type} {version} {0}").format(
        MessageChain(Plain("bars"), At(111111)),
        name="pog",
        type=Plain("coroutine"),
        version=MessageChain(Plain("3.2.1"), At(87654321)),
    )
)
