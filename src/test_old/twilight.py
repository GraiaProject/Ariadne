import devtools

from graia.amnesia.log import install
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import *
from graia.ariadne.message.parser.twilight import *

install()
if __name__ == "__main__":
    twilight_args_kwargs = Twilight(
        [
            FullMatch(".command"),
            1 @ ArgumentMatch("--option"),
            ElementMatch(type=At).param(2),
        ]
    )

    sparkle_kwargs = twilight_args_kwargs.generate(MessageChain(".command --option foo ", At(123)))
    devtools.debug(sparkle_kwargs)

    twilight_g = Twilight(
        [
            FullMatch(".command"),
            "boolean" @ ArgumentMatch("--option", action="store_true"),
            ElementMatch(type=At).param("at"),
        ]
    )

    sparkle_kwargs = twilight_g.generate(MessageChain(".command --option ", At(123)))
    devtools.debug(sparkle_kwargs)

    try:
        twilight_args_kwargs.generate(MessageChain(".coroutine hahaha"))
    except Exception as e:
        devtools.debug(e)

    sparkle_next = Twilight([FullMatch(".command"), "foo" @ ParamMatch()]).generate(
        MessageChain(".command opq")
    )
    devtools.debug(sparkle_next)

    twilight_assert = Twilight([RegexMatch(r"(?=.*a)(?=.*b)(?=.*c)(?=.*d)(?=.*e)"), WildcardMatch()])

    devtools.debug(twilight_assert.generate(MessageChain("abcde")))

    devtools.debug(
        Twilight(
            [FullMatch("lp"), FullMatch("user"), FullMatch("perm"), ParamMatch(), ParamMatch()]
        ).generate(MessageChain('lp user perm "set" "DENIED -> NOLOGIN"'))
    )

    sp = Twilight(
        [FullMatch("lp"), FullMatch("user"), ParamMatch(), FullMatch("set"), ParamMatch()]
    ).generate(MessageChain("lp user perm set 'DENIED -> NOLOGIN'"))

    devtools.debug(sp)

    flag_twi = Twilight(
        [
            FullMatch(".test").help("匹配 .test"),
            "op" << ParamMatch().help("操作符"),
            "help" @ ArgumentMatch("--help", "-h", action="store_true").help("显示该帮助"),
            "arg" @ WildcardMatch().flags(re.DOTALL),
            "v" << ArgumentMatch("--verbose", "-v", action="store_true").help("显示详细信息"),
        ]
    ).help(".test <op>", "描述", "总结", brief="测试测试!")

    devtools.debug(flag_twi.generate(MessageChain([".test op"])))

    devtools.debug(flag_twi.generate(MessageChain([".test op gl"])))

    flag_sp = flag_twi.generate(MessageChain([".test op\nop\nseq -v"]))
    devtools.debug(flag_sp.res)
