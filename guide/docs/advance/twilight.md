# Twilight - 混合式消息链处理器

> 本模块名字取自 [`My Little Pony`](https://mlp.fandom.com/wiki/My_Little_Pony_Friendship_is_Magic_Wiki) 中的 [`Twilight Twilight`](https://mlp.fandom.com/wiki/Twilight_Sparkle).
>
> Friendship is magic!

!!! warning "注意"

    本文档内容适用于 `Ariadne` `0.5.0+`.

## 缘起

想必 [`v4`](../../appendix/terms/#v4) 用户都或多或少的知道 `Kanata` 吧.

其介绍的 正则表达式 参数提取/关键字匹配 非常的有趣, 而 `Twilight` 在其基础上增加了对 `argparse` 中部分功能的支持.

## 创建 Twilight 类

`Twilight` 的最佳使用方式为继承 `Twilight` 类并通过 **类变量** 的形式定义匹配项.

之后在实例化时添加命令头.

```py
class FooCommand(Twilight):
    help = ArgumentMatch("--help", "-h", action="store_true")
    bar_match = FullMatch("_bar_")
    regex_match = RegexMatch(r"\d+")
    wildcard = WildcardMatch()

twilight = FooCommand([RegexMatch(r"[./!]header")]))
```

## 手动生成

在 `Twilight` 对象上调用 `generate(message_chain)` 即可手动生成 `Twilight` 而无需配合 `Broadcast`.

!!! info "提示"

    这在本地调试时非常有用.

    ??? example "效果"

        ```py
        >>> twilight.generate(MessageChain(["!header _bar_ 123 --help pwq external"]))

        FooCommand(
            [RegexMatch(matched=True, result=MessageChain([Plain(text='!header')]), pattern='[./!]header')],
            help=ArgumentMatch(matched=True, result=True, pattern=('--help', '-h')),
            bar_match=FullMatch(matched=True, result=MessageChain([Plain(text='_bar_')]), pattern='_bar_'),
            regex_match=RegexMatch(matched=True, result=MessageChain([Plain(text='123')]), pattern='\\d+'),
            wildcard=WildcardMatch(matched=True, result=MessageChain([Plain(text='pwq external')]), pattern='.*')
            )
        ```

        !!! info "这里换行和你看到的并不一样, 只是为了展示."

## Match

`Match` 本身仅为 抽象基类, 无法被直接实例化, 有以下几种变体:

- `RegexMatch` : 正则表达式匹配, 支持传入 `re.Flag`.
- `FullMatch` : 严格全匹配.
- `UnionMatch` : 多重全匹配, 即在传入的 `pattern` 中任意符合一种即可.
- `ElementMatch` : 元素匹配, 可匹配 `Plain` 以外的元素类型.
- `WildcardMatch` : 任意匹配, 可以通过 `greed` 参数确定是否贪婪匹配.
- `ArgumentMatch` : 参数匹配, 在 **`match` 字典 或 类变量** 中没有以上三种匹配时才允许不以 "-" 打头.

这些 `Match` 类可接受以下参数:

- `pattern` : 匹配项, 为一个字符串 (`ArgumentMatch` 与 `UnionMatch` 可为多个, `ElementMatch` 应传入类型而非字符串). **在 `WildcardMatch` 上不可用**
- `optional` : 是否可选, 在 `ArgumentMatch` 上会通过传入的 `pattern` 确定是否有效. (在非 `ArgumentMatch` 上默认为 False, 在 `ArgumentMatch` 上默认为 True.)
- `preserve_space` : 是否要预留尾随空格. **在 `ArgumentMatch` 上不可用**
- `help` : 帮助字符串, 在 `Twilight.get_help` 中使用.
- `alt_help` : 替代帮助字符串, 在 `Twilight.get_help` 中使用.

在完成 `Twilight` 生成后, `Twilight` 附带的 `Match` 有以下属性:

- `matched` : 标志着匹配到的对象是否有内容.
- `result` : 匹配结果.
- `regex_match` : 仅 `RegexMatch` 拥有, 为原来的 `re.Match` 对象.

## Twilight 的实例化

`Twilight` 在实例化时, 可接受一个 额外 **可迭代对象** `check` 与 额外字典 `match`, 作用如下：

- `check_args` 仅应当容纳 `RegexMatch` 与 `FullMatch` 对象, 用于对 `MessageChain` 进行预先检查

- `matches` 为一个 `Dict[str, Match]` 映射, 相当于拓展 `Twilight.__class__.__dict__`

比如, 这两种写法其实在 **运行时** 等价.

=== "使用 派生类"

    ```py
    class FooTwilight(Twilight):
        match = RegexMatch(r"\d+")

    t = FooTwilight([RegexMatch(r"[!.]header")])
    ```

=== "直接 实例化"

    ```py
    t = Twilight([RegexMatch(r"[!.]header")], {"match": RegexMatch(r"\d+")})
    ```

=== "派生类与间接实例化"

    ```py
    class FooTwilight(Twilight):
        match = RegexMatch(r"\d+")

    t = Twilight(FooTwilight([RegexMatch(r"[!.]header")]))
    t = Twilight(FooTwilight)
    ```

    !!! warning "注意这个操作只为向后兼容, 可能在任意时候移除。"

!!! warning "注意"

    如果你想要检查 "命令头", 请使用 `check` 而非向 `Twilight` 添加类变量.

    在 `check` 中的 `Match` 对象 `optional` 参数是无效的.

`Twilight` 在实例化时, 接受以下变体:

=== "check: Dict"

    ```py
    @overload
    def __init__(
        self,
        check: Dict[str, Match],
        *,
        remove_source: bool = True,
        remove_quote: bool = True,
        remove_extra_space: bool = False,
        description: str = "",
        epilog: str = "",
    ):
        """
        Args:
            check (Dict[str, Match]): 匹配的映射.
        """
    ```

=== "check: Twilight 类 或 Twilight 实例"

    ```py
    @overload
    def __init__(
        self,
        check: Union[Type[T_Twilight], T_Twilight],
        *,
        remove_source: bool = True,
        remove_quote: bool = True,
        remove_extra_space: bool = False,
        description: str = "",
        epilog: str = "",
    ):
        """
        Args:
            check (Union[Type[Twilight], Twilight], optional): 根 Twilight 实例, 用于生成新的 Twilight.
        """
    ```

=== "check: Iterable, match: Dict"

    ```py
    @overload
    def __init__(
        self,
        check: Iterable[RegexMatch],
        match: Dict[str, Match],
        *,
        remove_source: bool = True,
        remove_quote: bool = True,
        remove_extra_space: bool = False,
        description: str = "",
        epilog: str = "",
    ):
        """
        Args:
            check (Iterable[RegexMatch]): 用于检查的 Match 对象.
            match (Dict[str, Match]): 额外匹配的映射.
        """
    ```

- remove_source (bool, optional): 是否移除消息链中的 Source 元素. 默认为 True.
- remove_quote (bool, optional): 处理时是否要移除消息链的 Quote 元素. 默认为 True.
- remove_extra_space (bool, optional): 是否移除 Quote At AtAll 的多余空格. 默认为 False.
- description (str, optional): 本 Twilight 的前置描述, 在 `add_help` 中用到.
- epilog (str, optional): 本 Twilight 的后置描述, 在 `add_help` 中用到.

## 提取 Match 对象

`Match` 对象可以通过以下几种方式提取:

- 若是在实例化 `Twilight` 时通过 `check` 参数添加的, 那只能通过 `Twilight[int]` 的形式提取.
- 否则, 可通过 `Twilight[match_name]` 与 `Twilight.match_name` 两种方式提取.

## 配合 Broadcast 使用

`Twilight` 应作为 `dispatcher` 传入 `bcc.receiver` / `ListenerSchema` 中.

在 `receiver` 函数的类型标注中, 通过 标注参数为 `Twilight` 获取 `Twilight` 实例, 通过 `name: Match` 的形式获取 `name` 对应的匹配对象.

像这样:

```py hl_lines="2"
@bcc.receiver(MessageEvent, dispatchers=[
    Twilight(
        [FullMatch(".command")],
        {"arg": RegexMatch(r"\d+", optional=True)}
    )])
async def reply(..., arg: RegexMatch):
    ...
```

!!! note "使用 `Twilight` 与 `Match` 的子类进行标注也是可以的."

一旦匹配失败 (`gen_sparkle` 抛出异常), `Broadcast` 的本次执行就会被取消.

## 创建帮助

通过 `Twilight.get_help` 方法可以方便的获取帮助.

???+ example "示例"

    假设你想要创建一个可以显示通过 日期 显示 星期 的命令:

    ```py
    class Command(Twilight):
        date = RegexMatch(r"(?P<year>\d+)[.-](?P<month>\d+)[.-](?P<day>\d+)", help="日期的字符串")
        help = ArgumentMatch(
            "--help", "-h", action="store_true", help="显示本帮助."
        )  # 语法与 argparse.ArgumentParser.add_argument 基本相同
        # 注意 help 是手动添加的

    print(Command().get_help()) # 注意需要在 Twilight 实例上调用.
    ```

    效果如下:

    ```
    使用方法: (?P<year>\d+)[.-](?P<month>\d+)[.-](?P<day>\d+) [--help]

    位置匹配:
      date -> 匹配 (?P<year>\d+)[.-](?P<month>\d+)[.-](?P<day>\d+) : 日期的字符串

    参数匹配:
      --help, -h  显示本帮助.
    ```

### 使用 description, epilog 与 alt_help 控制帮助生成

回到刚才的示例.

我们可以通过 `description` 与 `epilog` 控制在帮助内容前后添加的文本.

=== "在定义类时传入"

    ```py
    class Command(Twilight, description=..., epilog=...):
        ...
    ```

=== "在实例化时传入"

    ```py
    Command(description=..., epilog=...).get_help()
    ```

=== "在调用 get_help 时传入"

    ```py
    Command().get_help(description=..., epilog=...)
    ```

从左往右, 优先级递增.

而 `Match` 的 `alt_help` 可以控制部分该匹配对象的帮助信息.

???+ 对比

    === "前"

        ```py
        class Command(Twilight):
            date = RegexMatch(r"(?P<year>\d+)[.-](?P<month>\d+)[.-](?P<day>\d+)", help="日期的字符串")
        ```

        ```
        使用方法: (?P<year>\d+)[.-](?P<month>\d+)[.-](?P<day>\d+)

        位置匹配:
          date -> 匹配 (?P<year>\d+)[.-](?P<month>\d+)[.-](?P<day>\d+) : 日期的字符串
        ```

    === "后"

        ```py
        class Command(Twilight):
            date = RegexMatch(r"(?P<year>\d+)[.-](?P<month>\d+)[.-](?P<day>\d+)",
            help="日期的字符串", alt_help="YYYY-MM-DD")
        ```

        ```
        使用方法: YYYY-MM-DD

        位置匹配:
          date -> 匹配 YYYY-MM-DD : 日期的字符串
        ```

你还可以通过 `header` 参数控制是否要显示 "使用方法" 一行.

## Twilight 的解析过程

在解析消息链时, `Twilight.generate` 会依照如下流程解析:

- 使用 `Twilight.populate_check_match` 解析 `Twilight` 的 `check_args`, 并返回剩下部分的列表. (使用 `split` 方法)
- 使用 `Twilight.populate_arg_match` 解析 `ArgumentMatch` 并从 `argparse.Namespace` 提取结果, 向 `ArgumentMatch.result` 赋值.
- 使用 `Twilight.populate_regex_match` 解析并赋值剩下的 `Match` 对象.

## 最佳实践

对于复杂的命令, 继承一个 `Twilight` 类是最好的.

无论是简单还是复杂的命令, 你应该且仅仅只应该把命令头放到 `check` 参数中, 任何程序应访问的 `Match` 对象都应放在 **类变量** 或 **`match` 字典** 里.

## 性能考量

你可以通过运行 `test/parser_performance.py` 来测试 `Twilight` 的性能.

在 `i5-10500` 处理器上, `Twilight` 的性能大约为 `3000 ~ 4000 msg/s`, 取决于 `Twilight` 的复杂程度.
