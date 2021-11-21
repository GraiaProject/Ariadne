import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))

from devtools import debug, version

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.component import Component
from graia.ariadne.message.element import At, P, Plain
from graia.ariadne.message.formatter import Formatter

debug(
    Formatter("{name} {type} {version} {0}").format(
        At(123456789),
        name=Plain("pog"),
        type=Plain("coroutine"),
        version=Plain("3.2.1"),
    )
)

debug(Component[Plain:1].select(MessageChain(["hello", At(123456), "hi"])))
