import devtools

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import *
from graia.ariadne.message.parser.twilight import *
from graia.ariadne.util import inject_loguru_traceback

inject_loguru_traceback()


class SparkleTest(Sparkle):
    arg_a = ArgumentMatch("--foo")
    arg_b = ArgumentMatch("--bar", action="append", regex=r"\d+")
    regex_a = RegexMatch(r"\d+")
    regex_b = RegexMatch(r"\d+")
    full_non_optional_a = FullMatch("Necessary")
    full_optional = FullMatch("Universe", optional=True)
    full_non_optional_b = FullMatch("Neck")


if __name__ == "__main__":
    twilight = Twilight(SparkleTest)
    tw_1 = twilight.generate(MessageChain.create("80 80NecessaryNeck"))
    devtools.debug(tw_1)
    devtools.debug(twilight.generate(MessageChain.create("80 80NecessaryUniverseNeck --foo hey --bar 00121")))
    try:
        devtools.debug(
            twilight.generate(MessageChain.create("80 80NecessaryUniverseNeck --foo hey --bar nope"))
        )
    except Exception as e:
        devtools.debug(e)

    twilight_args_kwargs = Twilight(
        Sparkle(
            [FullMatch(".command")],
            {"param": ArgumentMatch("--option"), "at": ElementMatch(type=At)},
        )
    )

    sparkle_kwargs = twilight_args_kwargs.generate(MessageChain.create(".command --option foo ", At(123)))
    devtools.debug(sparkle_kwargs)

    try:
        twilight_args_kwargs.generate(MessageChain.create(".coroutine hahaha"))
    except Exception as e:
        devtools.debug(e)

    sparkle_mixed = Twilight(
        Sparkle(match={"foo": ParamMatch("foo"), "bar": ArgumentMatch("--bar")})
    ).generate(MessageChain.create("test --bar opq"))
    devtools.debug(sparkle_mixed)

    sparkle_next = Twilight(Sparkle([FullMatch(".command")], match={"foo": ParamMatch("foo")})).generate(
        MessageChain.create(".command opq")
    )
    devtools.debug(sparkle_next)

    twilight_assert = Twilight(Sparkle([RegexMatch(r"(?=.*a)(?=.*b)(?=.*c)(?=.*d)(?=.*e)")]))

    devtools.debug(twilight_assert.generate(MessageChain.create("abcde")))

    class FooSparkle(Sparkle, description="Foo description", epilog="Foo epilog"):
        help = ArgumentMatch("--help", "-h", action="store_true", help="显示本帮助")
        foo = RegexMatch(".*", help="Foo help!", alt_help="instead")

    twilight = Twilight(FooSparkle([RegexMatch(r"[./!]header")]))

    devtools.debug(twilight.generate(MessageChain(["!header --help hello"])))
    devtools.debug(twilight.root._parser._actions)
    print(twilight.root.get_help())

    union_twi = Twilight(Sparkle(check=[UnionMatch(".hello", ".hi")]))
    devtools.debug(union_twi.generate(MessageChain([".hello"])))
    devtools.debug(union_twi.generate(MessageChain([".hi"])))
    try:
        devtools.debug(union_twi.generate(MessageChain([".help"])))
    except Exception as e:
        devtools.debug(e)

    class FooCommand(Sparkle):
        help = ArgumentMatch("--help", "-h", action="store_true")
        bar_match = FullMatch("_bar_")
        regex_match = RegexMatch(r"\d+")
        wildcard = WildcardMatch()

    k = Twilight(FooCommand([RegexMatch(r"[./!]header")])).generate(
        MessageChain(["!header _bar_ 123 --help pwq external"])
    )

    devtools.debug(k)

    devtools.debug(
        Twilight(
            Sparkle([FullMatch("lp"), FullMatch("user"), FullMatch("perm"), ParamMatch(), ParamMatch()])
        ).generate(MessageChain.create('lp user perm "set""DENIED -> NOLOGIN"'))
    )

    sp = Twilight(
        Sparkle([FullMatch("lp"), FullMatch("user"), ParamMatch(), FullMatch("set"), ParamMatch()])
    ).generate(MessageChain.create("lp user perm set 'DENIED -> NOLOGIN'"))

    devtools.debug(sp)
    devtools.debug(sp._match_ref)
    devtools.debug(sp.get_match(ParamMatch))
    devtools.debug(sp[ParamMatch, 0])

    flag_sp = Twilight(
        Sparkle(
            [FullMatch(".test")],
            {
                "help": ArgumentMatch("--help", "-h", action="store_true"),
                "arg": WildcardMatch(flags=re.DOTALL),
                "verbose": ArgumentMatch("--verbose", action="store_true"),
            },
        )
    )
    devtools.debug(flag_sp.generate(MessageChain([".test op\nop\nseq"])))

    devtools.debug(Sparkle.from_command("[lp|luckperm] {0} user {permission} [\{no_admin\}|no_admin] call "))
