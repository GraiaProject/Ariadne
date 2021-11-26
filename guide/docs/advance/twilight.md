# Twilight - 混合式消息链处理器

> 本模块名字取自 [`My Little Pony`](https://mlp.fandom.com/wiki/My_Little_Pony_Friendship_is_Magic_Wiki) 中的 [`Twilight Sparkle`](https://mlp.fandom.com/wiki/Twilight_Sparkle).
>
> Friendship is magic!

## 缘起

想必 [`v4`](./../appendix/terms.md/#v4) 用户都或多或少的知道 `Kanata` 吧.

其介绍的正则表达式匹配非常的有趣, 而 `Twilight` 在其基础上增加了对 `argparse` 中部分功能的支持.

## 使用

`Twilight` 的最佳使用方式为继承 `Sparkle` 类并通过 `类变量` 的形式定义匹配项.

像这样:

```py
from graia.ariadne.message.parser.twilight import Twilight, Sparkle

```
