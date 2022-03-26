# Twilight - 混合式消息链处理器

> 本模块名字取自 [`My Little Pony`](https://mlp.fandom.com/wiki/My_Little_Pony_Friendship_is_Magic_Wiki) 中的 [`Twilight Sparkle`](https://mlp.fandom.com/wiki/Twilight_Sparkle).
>
> Friendship is magic!

## 缘起

想必 [`v4`](../../appendix/terms/#v4) 用户都或多或少的知道 `Kanata` 吧.

其介绍的 正则表达式 参数提取/关键字匹配 非常的有趣, 而 `Twilight` 在其基础上增加了对 `argparse` 中部分功能的支持.

## 快速开始

```py
from graia.ariadne.message.parser.twilight import Twilight, FullMatch, ParamMatch, RegexResult

twilight = Twilight([FullMatch("指令"), ParamMatch() @ "param"])

@broadcast.receiver(GroupMessage, dispatchers=[twilight])
async def twilight_handler(event: GroupMessage, app: Ariadne, param: RegexResult):
    await app.sendMessage(event, "收到指令: " + param.result)
```

接下来, 让我们解析一下这段代码:

## 创建 Twilight

```py
twilight = Twilight([FullMatch("指令"), ParamMatch() @ "param"])
```

这里说明我们需要匹配内容为 "指令 xxx" 的消息, 并且把 "xxx" 作为参数传递给 `param` 变量.

`Twilight` 接受一个由 `Match` 组成的列表, 之后对于每条消息利用 [`re`][] 的正则表达式与 [`argparse`][argparse] 进行解析

!!! info "手动生成"

    在 `Twilight` 对象上调用 `generate(message_chain)` 即可手动生成
    [`Sparkle`][graia.ariadne.message.parser.twilight.Sparkle] 而无需配合 `Broadcast`.

    这对于本地调试很有用.

### 分配参数

```python
ParamMatch() @ "param"
```

这一段的 `ParamMatch() @ "param"` 说明这个参数传递给函数内的 `param` 形参.

也就是 `param: RegexResult` 这里.

与此同时, 以下用法等效.

```pycon
>>> ParamMatch().param("param")
>>> "param" @ ParamMatch()
>>> "param" << ParamMatch()
>>> ParamMatch() >> "param"
```

!!! warning "注意位移运算符 `>>` 与 `<<` 始终朝向字符串."

???+ info "为什么支持这些运算符? "

    `>>` 与 `<<` 支持的灵感源于其他语言中对于文件流的操作:

    ```C++
    cin >> var;
    cout << "value";
    ```

    我们借鉴了这些语言的设计, 将 `>>` 与 `<<` 的运算符设计为支持 `str` / `int` 类型以进行参数分派.

## Match

### RegexMatch

[`RegexMatch`][graia.ariadne.message.parser.twilight.RegexMatch] 是 `Twilight` 的基础, 它可以匹配指定的正则表达式.

[`FullMatch`][graia.ariadne.message.parser.twilight.FullMatch]
[`UnionMatch`][graia.ariadne.message.parser.twilight.UnionMatch]
[`ParamMatch`][graia.ariadne.message.parser.twilight.ParamMatch]
[`WildcardMatch`][graia.ariadne.message.parser.twilight.WildcardMatch]
都是基于 [`RegexMatch`][graia.ariadne.message.parser.twilight.RegexMatch] 的包装类.

- `FullMatch`: 完整匹配内容
- `UnionMatch`: 匹配多个内容
- `ParamMatch`: 匹配指定参数
- `WildcardMatch`: 匹配任意内容

#### flags 方法

可以通过 [`flags`][graia.ariadne.message.parser.twilight.RegexMatch.flags] 方法设置正则表达式的匹配标记.

```pycon
>>> RegexMatch(r"\d+ # digits").flags(re.V) # 设置 re.VERBOSE 标记
```

#### space 方法

[`SpacePolicy`][graia.ariadne.message.parser.twilight.SpacePolicy] 是一个 [`enum.Enum`][enum.Enum] 类, 有如下常量:

- `NOSPACE`: 不附带尾随空格.
- `PRESERVE`: 预留尾随空格. (默认)
- `FORCE`: 强制需要尾随空格.

它们应被作为 **不透明对象** 使用.

[`SpacePolicy`][graia.ariadne.message.parser.twilight.SpacePolicy]
应该传递给
[`RegexMatch.space`][graia.ariadne.message.parser.twilight.RegexMatch.space]
方法, 用于确定 `RegexMatch` 尾随空格策略.

### ArgumentMatch

`ArgumentMatch` 思路与 `RegexMatch` 不同, 它基于 [argparse][] 进行参数解析.

[`ArgumentMatch`][graia.ariadne.message.parser.twilight.ArgumentMatch]
的初始化方法与 [add_argument][argparse.ArgumentParser.add_argument] 非常相似.

受限于篇幅, 这里没法详细展开. 只能给出几个用例:

```pycon
>>> ArgumentMatch("-s", "--switch", action="store_true") # 开关
>>> ArgumentMatch("-o", "--opt", type=str, choices=["head", "body"]) # 只允许 "head" 或 "body"
>>> ArgumentMatch("-m", choices=MessageChain(["choice_a", "choice_b"])) # 注意默认是 MessageChain, 所以要这样写
```

## 配合 Broadcast 使用

`Twilight` 应作为 `dispatcher` 传入 `broadcast.receiver` / `ListenerSchema` 中.

在 `receiver` 函数的类型标注中, 通过 标注参数为 `Sparkle` 获取当前 `Sparkle`, 通过 `name: Match` 的形式获取 `name` 对应的匹配对象.

像这样:

```py
@broadcast.receiver(MessageEvent, dispatchers=[
        Twilight(
            [
                FullMatch(".command"),
                "arg" @ RegexMatch(r"\d+", optional=True)
            ]
        )
    ]
)
async def reply(..., arg: RegexResult):
    ...
```

!!! note "使用 `Sparkle`, `Match`, `MatchResult` 的子类进行标注都是可以的."

一旦匹配失败 (`generate` 抛出异常), `Broadcast` 的本次执行就会被取消.

### MatchResult

`RegexResult` 与 `ArgResult` 都是 [`MatchResult`][graia.ariadne.message.parser.twilight.MatchResult] 的子类.

这二者方便地标注了匹配结果信息.

`MatchResult` 的属性:

- `MatchResult.matched`: 对应的 `Match` 对象是否匹配.
- `MatchResult.origin`: 原始 `Match` 对象.
- `MatchResult.result`: 匹配结果.

### ResultValue 装饰器

`ResultValue` 作为装饰器使用, 可以直接获取匹配结果而不需要从 `Match.result` 提取.

```py hl_lines="10"
@broadcast.receiver(MessageEvent, dispatchers=[
        Twilight(
            [
                FullMatch(".command"),
                "arg" @ RegexMatch(r"\d+", optional=True)
            ]
        )
    ]
)
async def reply(..., arg: MessageChain = ResultValue()): # 保证不会被正常的流程覆盖
    ...
```

## int 类型的参数名

你可以这样: `#!py ParamMatch() @ 1`

之后获取 [`Sparkle`][graia.ariadne.message.parser.twilight.Sparkle] 对象, 并对其进行索引操作.

```py
p: RegexResult = Sparkle[1]
```

这里只是顺嘴一提，因为有些时候这个不如 `str` 来的方便.

## 生成帮助

使用 [`Twilight.get_help`][graia.ariadne.message.parser.twilight.Twilight.get_help] 可以获得帮助文本(已进行缩进处理).

对于 `ArgumentMatch`, 结果与 [`argparse.ArgumentParser.format_help`][argparse.ArgumentParser.format_help] 相近.

`RegexMatch` 会在有参数分发位置时显示其分发目标. ( `name -> help` 形式)

`sep` 控制了 `name -> help` 格式中 使用的分割形式 (默认为 `#!py " -> "`)

如果没有通过 `help` 方法传入帮助字符串, 则 `UnionMatch` 与 `ParamMatch` 会尝试生成一个 (`ParamMatch` 为 `#!py "参数"`, `UnionMatch` 会从 `pattern` 推断).

否则, 该 `RegexMatch` 会被忽略.

传入的 `usage` 后会添加上来自 `argparse` 自动生成的参数选项, 所以 `usage` 中只应描述 `RegexMatch` 提供的匹配.

`description` 与 `epilog` 参数含义与 [`argparse.ArgumentParser`][argparse.ArgumentParser] 中语义相同.

你可以通过下面的实例看看它的效果:

```pycon
>>> print(
...     Twilight(
...         [
...             FullMatch(".test").help("匹配 .test"),
...             "union" @ UnionMatch("A", "B", "C"),
...             "at" @ ElementMatch(At),
...             "op1" @ ParamMatch(),
...             "op2" @ ParamMatch().help("操作符"),
...             "help" @ ArgumentMatch("--help", "-h", action="store_true").help("显示该帮助"),
...             "arg" @ WildcardMatch().flags(re.DOTALL),
...             "v" @ ArgumentMatch("--verbose", "-v", action="store_true").help("显示详细信息"),
...         ]
...     ).get_help("用法字符串", "描述", "总结")
... )
用法字符串 [--help] [--verbose]

描述

匹配项:
  匹配 .test

  union -> 在 ['A', 'B', 'C'] 中选择一项

  at -> At 元素

  op1 -> 参数

  op2 -> 操作符

可选参数:
  --help, -h     显示该帮助
  --verbose, -v  显示详细信息

总结

```
