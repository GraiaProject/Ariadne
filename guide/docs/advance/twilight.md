# Twilight - 混合式消息链处理器

> 本模块名字取自 [`My Little Pony`](https://mlp.fandom.com/wiki/My_Little_Pony_Friendship_is_Magic_Wiki) 中的 [`Twilight Sparkle`](https://mlp.fandom.com/wiki/Twilight_Sparkle).
>
> Friendship is magic!

## 缘起

想必 [`v4`](../../appendix/terms/#v4) 用户都或多或少的知道 `Kanata` 吧.

其介绍的正则表达式匹配非常的有趣, 而 `Twilight` 在其基础上增加了对 `argparse` 中部分功能的支持.

## 使用

`Twilight` 的最佳使用方式为继承 `Sparkle` 类并通过 `类变量` 的形式定义匹配项.

之后在实例化 `Sparkle` 时添加命令头.

??? "示例"

    假设你想要创建一个可以显示通过 日期 显示 星期 的命令:

    ```py
    from graia.ariadne.message.parser.twilight import Twilight, Sparkle
    from graia.ariadne.message.parser.pattern import RegexMatch, ArgumentMatch
    from graia.ariadne.event.message import MessageEvent
    from graia.broadcast import Broadcast

    from graia.ariadne.app import Ariadne


    class CommandSparkle(Sparkle):
        date = RegexMatch(r"(?P<year>\d+)[.-](?P<month>\d+)[.-](?P<day>\d+)")
        help = ArgumentMatch(
            "--help", "-h", action="store_true"
        )  # 语法与 argparse.ArgumentParser.add_argument 基本相同
        # 注意 help 是手动添加的


    if __name__ == "__main__":
        from graia.ariadne.message.chain import MessageChain
        import datetime

        bcc: Broadcast = ...

        @bcc.receiver(
            MessageEvent,
            dispatchers=Twilight(CommandSparkle([RegexMatch("[.!/]convert[_-]date")])),
        )
        async def convert(
            app: Ariadne, event: MessageEvent, date: RegexMatch, sparkle: CommandSparkle
        ):
            if not date.matched or sparkle.help.result:
                await app.sendMessage(event, MessageChain.create(sparkle.get_help()))
                return
            weekday = datetime.date.fromisoformat(
                f"{date.regex_match.group('year')}-{date.regex_match.group('month')}-{date.regex_match.group('day')}"
            ).weekday()

            weekday = weekday or 7

            await app.sendMessage(
                MessageChain.create(f"{date.regex_match.group()}是 星期 {weekday}")
            )
    ```
