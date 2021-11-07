import os
import sys

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))

import devtools

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import *
from graia.ariadne.message.parser.pattern import *
from graia.ariadne.message.parser.twilight import Sparkle, Twilight


class SparkleTest(Sparkle):
    arg_a = ArgumentMatch("--foo")
    arg_b = ArgumentMatch("--bar", action="append", regex="\d+")
    regex_a = RegexMatch(r"\d+")
    space = FullMatch(" ")
    regex_b = RegexMatch(r"\d+")
    full_non_optional_a = FullMatch("NecessaryTest")
    full_optional = FullMatch("Universe", optional=True)
    full_non_optional_b = FullMatch("NecessaryTest_2")


if __name__ == "__main__":
    twilight = Twilight(SparkleTest)
    tw_1 = twilight.gen_sparkle(
        MessageChain.create("80 80NecessaryTestNecessaryTest_2")
    )
    devtools.debug(tw_1)
    devtools.debug(
        twilight.gen_sparkle(
            MessageChain.create(
                "80 80NecessaryTestUniverseNecessaryTest_2 --foo hey --bar 00121"
            )
        )
    )
    try:
        devtools.debug(
            twilight.gen_sparkle(
                MessageChain.create(
                    "80 80NecessaryTestUniverseNecessaryTest_2 --foo hey --bar nope"
                )
            )
        )
    except Exception as e:
        devtools.debug(e)

    twilight_args_kwargs = Twilight(
        Sparkle([FullMatch(".command")], {"param": ArgumentMatch("--option")})
    )
    sparkle_kwargs = twilight_args_kwargs.gen_sparkle(
        MessageChain.create(".command --option foo", At(123))
    )
    devtools.debug(sparkle_kwargs)
