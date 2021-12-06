import devtools

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import *
from graia.ariadne.message.parser.pattern import *
from graia.ariadne.message.parser.twilight import Sparkle, Twilight


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
            {"param": ArgumentMatch("--option"), "at": ArgumentMatch("at", type=At)},
        )
    )

    sparkle_kwargs = twilight_args_kwargs.generate(MessageChain.create(".command --option foo ", At(123)))
    devtools.debug(sparkle_kwargs)

    try:
        twilight_args_kwargs.generate(MessageChain.create(".coroutine hahaha"))
    except Exception as e:
        devtools.debug(e)

    sparkle_mixed = Twilight(
        Sparkle(match={"foo": ArgumentMatch("foo"), "bar": ArgumentMatch("bar")})
    ).generate(MessageChain.create("test --bar opq"))
    devtools.debug(sparkle_mixed)

    sparkle_next = Twilight(Sparkle([FullMatch(".command")], match={"foo": ArgumentMatch("foo")})).generate(
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
    devtools.debug(twilight._root._parser._actions)
    print(twilight._root.get_help())

    union_twi = Twilight(Sparkle(check=[UnionMatch(".hello", ".hi")]))
    devtools.debug(union_twi.generate(MessageChain([".hello"])))
    devtools.debug(union_twi.generate(MessageChain([".hi"])))
    try:
        devtools.debug(union_twi.generate(MessageChain([".help"])))
    except Exception as e:
        devtools.debug(e)

    class FooCommand(Twilight):
        help = ArgumentMatch("--help", "-h", action="store_true")
        bar_match = FullMatch("_bar_")
        regex_match = RegexMatch(r"\d+")
        wildcard = WildcardMatch()

    k = FooCommand([RegexMatch(r"[./!]header")]).generate(
        MessageChain(["!header _bar_ 123 --help pwq external"])
    )

    print(repr(k))
