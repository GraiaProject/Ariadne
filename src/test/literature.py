import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain
from graia.ariadne.message.parser.literature import Literature
from graia.ariadne.message.parser.pattern import BoxParameter, SwitchParameter

if __name__ == "__main__":
    from graia.ariadne.message.element import At

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
