# Twilight - 混合式消息链处理器

> 本模块名字取自 [`My Little Pony`](https://mlp.fandom.com/wiki/My_Little_Pony_Friendship_is_Magic_Wiki) 中的 [`Twilight Sparkle`](https://mlp.fandom.com/wiki/Twilight_Sparkle).
>
> Friendship is magic!

## 缘起

想必 [`v4`](../../appendix/terms/#v4) 用户都或多或少的知道 `Kanata` 吧.

其介绍的 正则表达式 参数提取/关键字匹配 非常的有趣, 而 `Twilight` 在其基础上增加了对 `argparse` 中部分功能的支持.

## 快速开始

```py
from graia.ariadne.message.parser.twilight import Twilight, FullMatch, ParamMatch


twilight = Twilight([FullMatch("指令"), ParamMatch() @ "param"])

@broadcast.receiver(GroupMessage, dispatchers=[twilight])
async def twilight_handler(event: GroupMessage, app: Ariadne, param: MatchResult[MessageChain]):
    await app.sendMessage(event, "收到指令: " + param.result)
```