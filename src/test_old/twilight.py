import devtools

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import *
from graia.ariadne.message.parser.twilight import *
from graia.ariadne.util import inject_loguru_traceback

inject_loguru_traceback()

if __name__ == "__main__":
    twilight_args_kwargs = Twilight(
        [
            FullMatch(".command"),
            1 @ ArgumentMatch("--option"),
            ElementMatch(type=At).param(2),
        ]
    )

    sparkle_kwargs = twilight_args_kwargs.generate(MessageChain.create(".command --option foo ", At(123)))
    devtools.debug(sparkle_kwargs)

    twilight_g = Twilight(
        [
            FullMatch(".command"),
            "boolean" @ ArgumentMatch("--option", action="store_true"),
            ElementMatch(type=At).param("at"),
        ]
    )

    sparkle_kwargs = twilight_g.generate(MessageChain.create(".command --option ", At(123)))
    devtools.debug(sparkle_kwargs)

    try:
        twilight_args_kwargs.generate(MessageChain.create(".coroutine hahaha"))
    except Exception as e:
        devtools.debug(e)

    sparkle_next = Twilight([FullMatch(".command"), "foo" @ ParamMatch()]).generate(
        MessageChain.create(".command opq")
    )
    devtools.debug(sparkle_next)

    twilight_assert = Twilight([RegexMatch(r"(?=.*a)(?=.*b)(?=.*c)(?=.*d)(?=.*e)"), WildcardMatch()])

    devtools.debug(twilight_assert.generate(MessageChain.create("abcde")))

    devtools.debug(
        Twilight(
            [FullMatch("lp"), FullMatch("user"), FullMatch("perm"), ParamMatch(), ParamMatch()]
        ).generate(MessageChain.create('lp user perm "set" "DENIED -> NOLOGIN"'))
    )

    sp = Twilight(
        [FullMatch("lp"), FullMatch("user"), ParamMatch(), FullMatch("set"), ParamMatch()]
    ).generate(MessageChain.create("lp user perm set 'DENIED -> NOLOGIN'"))

    devtools.debug(sp)

    flag_sp = Twilight(
        [
            FullMatch(".test"),
            "help" @ ArgumentMatch("--help", "-h", action="store_true"),
            "arg" @ WildcardMatch().flags(re.DOTALL),
            "verbose" @ ArgumentMatch("--verbose", action="store_true"),
        ]
    ).generate(MessageChain([".test op\nop\nseq"]))
    devtools.debug(flag_sp.res)
