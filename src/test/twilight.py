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
    tw_1 = twilight.gen_sparkle(MessageChain.create("80 80NecessaryNeck"))
    devtools.debug(tw_1)
    devtools.debug(
        twilight.gen_sparkle(MessageChain.create("80 80NecessaryUniverseNeck --foo hey --bar 00121"))
    )
    try:
        devtools.debug(
            twilight.gen_sparkle(MessageChain.create("80 80NecessaryUniverseNeck --foo hey --bar nope"))
        )
    except Exception as e:
        devtools.debug(e)

    twilight_args_kwargs = Twilight(
        Sparkle(
            [FullMatch(".command")],
            {"param": ArgumentMatch("--option"), "at": ElementMatch(At, optional=True)},
        )
    )

    sparkle_kwargs = twilight_args_kwargs.gen_sparkle(MessageChain.create(".command --option foo ", At(123)))
    devtools.debug(sparkle_kwargs)

    try:
        twilight_args_kwargs.gen_sparkle(MessageChain.create(".coroutine hahaha"))
    except Exception as e:
        devtools.debug(e)

    sparkle_mixed = Twilight(
        Sparkle(matches={"foo": ArgumentMatch("foo"), "bar": ArgumentMatch("bar")})
    ).gen_sparkle(MessageChain.create("test --bar opq"))
    devtools.debug(sparkle_mixed)

    sparkle_next = Twilight(
        Sparkle([FullMatch(".command")], matches={"foo": ArgumentMatch("foo")})
    ).gen_sparkle(MessageChain.create(".command opq"))
    devtools.debug(sparkle_next)

    twilight_assert = Twilight(Sparkle([RegexMatch(r"(?=.*a)(?=.*b)(?=.*c)(?=.*d)(?=.*e)")]))

    devtools.debug(twilight_assert.gen_sparkle(MessageChain.create("abcde")))

    class FooSparkle(Sparkle):
        help = ArgumentMatch("--help", "-h", action="store_true")
        bar_match = FullMatch("_bar_")
        regex_match = RegexMatch(r"\d+")
        wildcard = WildcardMatch()

    twilight = Twilight(FooSparkle([RegexMatch(r"[./!]header")]))

    devtools.debug(twilight.gen_sparkle(MessageChain(["!header _bar_ 123 --help external"])))
