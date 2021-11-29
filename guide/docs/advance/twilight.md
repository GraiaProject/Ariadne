# Twilight - 混合式消息链处理器

> 本模块名字取自 [`My Little Pony`](https://mlp.fandom.com/wiki/My_Little_Pony_Friendship_is_Magic_Wiki) 中的 [`Twilight Sparkle`](https://mlp.fandom.com/wiki/Twilight_Sparkle).
>
> Friendship is magic!

## 缘起

想必 [`v4`](../../appendix/terms/#v4) 用户都或多或少的知道 `Kanata` 吧.

其介绍的 正则表达式 参数提取/关键字匹配 非常的有趣, 而 `Twilight` 在其基础上增加了对 `argparse` 中部分功能的支持.

## 创建 Sparkle 类

`Twilight` 的最佳使用方式为继承 `Sparkle` 类并通过 **类变量** 的形式定义匹配项.

之后在实例化 `Sparkle` 时添加命令头.

```py
class FooSparkle(Sparkle):
    help = ArgumentMatch("--help", "-h", action="store_true")
    bar_match = FullMatch("_bar_")
    regex_match = RegexMatch(r"\d+")
    wildcard = WildcardMatch()

twilight = Twilight(FooSparkle([RegexMatch(r"[./!]header")]))
```

## 手动生成

在 `Twilight` 对象上调用 `gen_sparkle(message_chain)` 即可手动生成 `Sparkle` 而无需配合 `Broadcast`.

!!! info "提示"

    这在本地调试时非常有用.

    ??? example "效果"

        ```py
        >>> twilight.gen_sparkle(MessageChain(["!header _bar_ 123 --help pwq external"]))

        FooSparkle(
            [RegexMatch(matched=True, result=MessageChain([Plain(text='!header')]), pattern=...)], # 注意这个.
            help=ArgumentMatch(matched=True, result=True, pattern=...),
            bar_match=FullMatch(matched=True, result=MessageChain([Plain(text='_bar_')]), pattern=...),
            regex_match=RegexMatch(matched=True, result=MessageChain([Plain(text='123')]), pattern=...),
            wildcard=WildcardMatch(matched=True, result=MessageChain([Plain(text='external')]), pattern=...)
            )
        ```

## Match

`Match` 本身仅为 抽象基类, 无法被直接实例化, 有以下几种变体:

- `FullMatch` : 严格全匹配.
- `RegexMatch` : 正则表达式匹配, 支持传入 `re.Flag`.
- `ElementMatch` : 元素匹配, 可匹配 `Plain` 以外的元素类型.
- `WildcardMatch` : 任意匹配, 可以通过 `greed` 参数确定是否贪婪匹配.
- `ArgumentMatch` : 参数匹配, 在 **`match` 字典 或 类变量** 中没有以上三种匹配时才允许不以 "-" 打头.

这些 `Match` 类可接受以下参数:

- `pattern` : 匹配项, 为一个字符串 (`ArgumentMatch` 可为多个, `ElementMatch` 应传入类型而非字符串). **在 `WildcardMatch` 上不可用**
- `optional` : 是否可选, 在 `ArgumentMatch` 上会通过传入的 `pattern` 确定是否有效. (在非 `ArgumentMatch` 上默认为 False)
- `preserve_space` : 是否要预留尾随空格. **在 `ArgumentMatch` 上不可用**
- `help` : 帮助字符串, 在 `Sparkle.get_help` 中使用.

在完成 `Sparkle` 生成后, `Sparkle` 附带的 `Match` 有以下属性:

- `matched` : 标志着是否成功匹配到
- `result` : 匹配结果
- `regex_match` : 仅 `RegexMatch` 拥有, 为原来的 `re.Match` 对象.

## Twilight 与 Sparkle 的实例化

`Sparkle` 在实例化时, 可接受一个 额外 **可迭代对象** `check_args` 与 额外字典 `matches`, 作用如下：

- `check_args` 仅应当容纳 `RegexMatch` 与 `FullMatch` 对象, 用于对 `MessageChain` 进行预先检查

- `matches` 为一个 `Dict[str, Match]` 映射, 相当于拓展 `sparkle.__class__.__dict__`

!!! error "注意"

    在 `0.4.4` 前, `check_args` 仅可传入 `Iterable[Match]`.

    `0.4.4` 后, `Sparkle` 在必要时会自动交换 `check_args` 与 `matches`.

比如, 这两种写法其实在 **运行时** 等价.

=== "使用 派生类"

    ```py
    class TSparkle(Sparkle):
        match = RegexMatch(r"\d+")

    s = TSparkle([RegexMatch(r"[!.]header")])
    ```

=== "直接 实例化"

    ```py
    s = Sparkle([RegexMatch(r"[!.]header")], {"match": RegexMatch(r"\d+")})
    ```

!!! warning "注意"

    如果你想要检查 "命令头", 请使用 `check_args` 而非向 `Sparkle` 添加类变量.

    在 `check_args` 中的 `Match` 对象 `optional` 参数是无效的 (永远为 False).

`Twilight` 在实例化时, 接受以下参数:

- `sparkle`: `Sparkle` 类 或 `Sparkle` 对象.
- `remove_source` , `remove_quote` , `remove_extra_space`:
  与 `Message.asMappingString` 中的含义相同, 但这些参数并不会影响通过 `MessageChain` 类型标注获取的消息链.

## 提取 Match 对象

`Match` 对象可以通过以下几种方式提取:

- 若是在实例化 `Sparkle` 时添加的, 那只能通过 `Sparkle[int]` 的形式提取.
- 否则, 可通过 `Sparkle[match_name]` 与 `Sparkle.match_name` 两种方式提取.

## 配合 Broadcast 使用

`Twilight` 应作为 `dispatcher` 传入 `bcc.receiver` / `ListenerSchema` 中.

在 `receiver` 函数的类型标注中, 通过 标注参数为 `Sparkle` 获取当前 `Sparkle`, 通过 `name: Match` 的形式获取 `name` 对应的匹配对象.

!!! note "使用 `Sparkle` 与 `Match` 的子类进行标注也是可以的."

一旦匹配失败 (`gen_sparkle` 抛出异常), `Broadcast` 的本次执行就会被取消.

## 创建帮助 (0.4.3+)

通过 `Sparkle.get_help` 方法可以方便的获取帮助.

???+ example "示例"

    假设你想要创建一个可以显示通过 日期 显示 星期 的命令:

    ```py
    class CommandSparkle(Sparkle):
        date = RegexMatch(r"(?P<year>\d+)[.-](?P<month>\d+)[.-](?P<day>\d+)", help="日期的字符串")
        help = ArgumentMatch(
            "--help", "-h", action="store_true", help="显示本帮助."
        )  # 语法与 argparse.ArgumentParser.add_argument 基本相同
        # 注意 help 是手动添加的

    print(CommandSparkle().get_help()) # 注意需要在 Sparkle 实例上调用.
    ```

    效果如下:

    ```
    使用方法: (?P<year>\d+)[.-](?P<month>\d+)[.-](?P<day>\d+) [--help]

    位置匹配:
      date -> 匹配 (?P<year>\d+)[.-](?P<month>\d+)[.-](?P<day>\d+) : 日期的字符串

    参数匹配:
      --help, -h  显示本帮助.
    ```

## Sparkle 的解析过程

在解析消息链时, `Twilight.gen_sparkle` 会依照如下流程解析:

- 使用 `Sparkle.run_check` 解析 `Sparkle` 的 `check_args`, 并返回剩下部分的列表. (使用 `split` 方法)
- 使用 `Sparkle.parse_arg_list` 解析 `ArgumentMatch` 并从 `argparse.Namespace` 提取结果, 向 `ArgumentMatch.result` 赋值.
- 使用 `Sparkle.match_regex` 解析并赋值剩下的 `Match` 对象.

## 最佳实践

对于复杂的命令, 继承一个 `Sparkle` 类是最好的.

无论是简单还是复杂的命令, 你应该且仅仅只应该把命令头放到 `match_args` 参数中, 任何程序应访问的 `match` 对象都应放在 **类变量** 或 **`matches` 字典** 里.
