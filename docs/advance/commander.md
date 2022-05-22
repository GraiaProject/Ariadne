# Commander - 便捷的命令触发系统

## 在开始之前

现在 `Ariadne` 的命令解析实现方式异常丰富.

- 最简单的指令解析: `DetectPrefix` 与 `DetectSuffix`, 看 [上一章](./../basic/base-parser.md)

- 最简洁 / 基于 `pydantic` `BaseModel` 的指令处理器: `Commander`

- 基于正则表达式的解析 / 容错性高且易于编写的处理器: [`Twilight`](./twilight.md)

- 支持子命令解析 / 基于 dict 的高度定制解析: [`Alconna`](./alconna/quickstart.md)

按照你的需求, 选择最适合你的处理器.

## 开始使用

!!! graiax "社区提示"

    本文档中含有以下可能让人不适的信息:

    - 令人费解的 `ABNF` 标注
    - 大量限制与变体 <span class="curtain">就像____学科一样</span>
    - 大量术语
    - 杂乱无章的排版

    请移步 [社区文档](https://graiax.cn/guide/commander.html) 获得更轻松的阅读体验.

`#!python from graia.ariadne.message.commander import Commander, Slot, Arg`

`Commander` 需要传入一个 `Broadcast` 对象以初始化, 并且会注册 `MessageEvent` 消息处理器.

```py
broadcast = Broadcast(...)

cmd = Commander(broadcast)
```

### `command` 方法

`Commander.command` 主要作为装饰器使用, 用于注册命令.

其 `dispatchers` `decorators` 两个参数与 `Broadcast.receiver` 含义相同, 这里不再详细讲解.

其 `command` 参数为一个字符串, 为类似 `shell` 的主命令样式.

其抽象文法表示如下:

```ABNF
CONSTANT ::= 任意非空且不包含 "[]{}|:" 这些符号的字符串
CHOICE ::= "[" CONSTANT ("|" CONSTANT)* "]"
PARAMETER ::= "{" ["..."] <标识符> [":" 类型标注] ["=" 默认值] "}"
SEGMENT ::= CONSTANT | CHOICE | PARAMETER
COMMAND ::= <SEGMENT> (" " SEGMENT)*
```

<span class="curtain">一部分懂 ABNF 的可能要开始骂街了</span>

<span class="curtain">我知道你没看懂对吧, 没关系, 我也不知道我写了什么</span>

我们先来看一个简单的例子:

```py
[.help | .h] text {content}
```

它接受以下样式的文本:

=== "A"

    ```#!text .help text function```

=== "B"

    ```#!text .h text parameter```

=== "C"

    ```#!text .h text "content_1 content_2"```

但是它不接受 ```#!text .help text func param```.


可以看出来,

`[.help | .h]` 这种用 **中括号** 括住的代表 **任选一个匹配**

`text` 这种纯文本的代表 **完全匹配**

`{content}` 这种用 **大括号** 括住的代表 **参数定义** .

而这些命令段之间使用空格分开.

`setting` 则是一个 `str` 至 `Slot | Arg` 映射, `str` 为实际参数名.

```py title="示例"
@cmd.command(".cmd {placeholder}", {"param": Slot("placeholder", str, "")})
async def func(param: str): ...
```

### 参数分派与标注

使用 **参数定义** 的拓展语法, 可以指定参数的类型与默认值, 并且让其不需要 [参数重定向](./#slot) 就可以直接被分派.

这种语法与 Python 中的标注语法相同. 例如: `#!py {content: str = "default"}`

它可以为 `#!py def (content: str) -> ...` 进行参数分派.

前导的 `...` 声明启用了 `wildcard`, 接受任意个尾接消息链, 在这个情况下可以进一步启用 `raw`.

#### 关于 wildcard

`wildcard` 模式可以类比 `#!py def func(*args: anno)` 中的 `*args`.

这种情况下接受任意个参数, 并通过 `{...param: anno}` 中的 `anno` 逐个处理.

最后分派的将是 `Tuple[anno]` 类型参数.

显而易见的, `default` 在 `wildcard` 下不可被设置.

通过 `#!py {...content: raw}` 这种特殊格式可以启用 [`raw`](./#raw) 解析模式.

#### 参数的自动解析

`Commander` 内部用了某些魔法自动解析参数并转换为对应的 Python 对象.

```py title="示例"
class ExampleModel(BaseModel):
    ...

@cmd.command(".command {content: ExampleModel = ExampleModel(...)}")
```

!!! info "请使用 `\\` 双重转义字符来转义 `[]{}` 符号 (可像正则表达式一样使用 `#!py r''` 修饰标记)"

    `#!py @cmd.command(r".command {content: List\[str\]}")`

!!! info "主命令还可以通过函数标注自动推断类型与默认值"

    ```py
    @cmd.command(".command {content: ExampleModel = ExampleModel(...)}")
    def func(content): ...
    ```

    等价于

    ```py
    @cmd.command(".command {content}")
    def func(content: ExampleModel = ExampleModel(...)): ...
    ```

    本机制并不会与 `Decorator` 解析冲突.


### 参数重定向: `Slot` 的使用

`Slot` 指定了它需要的 `placeholder`, 参数的类型, 以及 (可选的) 默认值.

主命令各个参数的优先级如下:

函数声明 < 命令的拓展语法 < Slot 定义

#### 最后一个参数: 可选项与 `raw` 属性

在 `Slot` 上指定 `default` / `default_factory` 即默认认为是可选项, 且要求其对应的参数在最后.

指定 `Slot` 的 `type` 为字面值 `#!py "raw"` <span class="curtain">或者 commander._raw</span> 时,
会认为 `Slot` 为 `raw`.

`raw` 模式下, 末尾 `wildcard` 的消息链元组会被转化为原来的单个消息链.

### 动态选项: `Arg`

`Arg` 必须指定 `default` (`default_factory`) 值作为没有该参数时的选项。

`Arg` 的 `pattern` 必须由 **单个** 选择匹配或完全匹配开头, 之后紧跟任意个 **参数定义** .

```ABNF
CONSTANT ::= 任意非空且不包含 "[]{}|:" 这些符号的字符串
CHOICE ::= "[" CONSTANT ("|" CONSTANT)* "]"
PLACEHOLDER ::= "{"CONSTANT"}"
ARG ::= <CONSTANT | CHOICE> (" " PLACEHOLDER)*
```

!!! warning "Arg 没有拓展语法, 且函数标注推断对其无效"

`Arg` 的 `type` 在单参数/无参数时可以省略, 在多参数时必须指定, 且为 `pydantic.BaseModel` 子类.

这个子类需要接受所有 `placeholder` 字段.

```py title="示例" hl_lines="2"
class ExampleModel(BaseModel):
    _ = pydantic.validator("*", pre=True, allow_reuse=True)(chain_validator)
    value: str = ""
    name: str = ""

Arg("[.option|--option|+O] {name} {value}", type=ExampleModel, default=ExampleModel())
```

在无参数时, `Arg` 的 `type` 为 `#!py bool` 类型, 而 `default` 默认为 `False` 且会自动反转.

```py title="示例"
Arg("--option") # 默认为 False, 出现时为 True

Arg("--option", default=True) # 默认为 True, 出现时为 False
```

单参数时 `Arg` 的 `type` 可以是 `BaseModel` 子类或者任意类型, 默认为 `MessageChain`.

```py title="示例"
Arg("--option {value}", type=str, default="")

Arg("--option {value}", default=MessageChain(["default"])) # 默认 type 为 MessageChain
```


### `add_type_cast`: 添加可处理的类型

`Commander` 之下, `pydantic` 处理了大部分数据的处理工作, 对于一些特殊的类型, 你可以通过 `add_type_cast` 添加自定义的转换函数.

!!! warning "add_type_cast 接受的函数会通过 [`pydantic.validator`](https://pydantic-docs.helpmanual.io/usage/validators/) 转换, 请注意其规范."

```py title="示例"
def cast_to_list(value: MessageChain, field: ModelField):
    if field.outer_type_ is List[str]:
        return value.asDisplay().split(".")
    if field.outer_type_ is List[MessageChain]:
        return value.split(".")
    return value

cmd.add_type_cast(cast_to_list)
```

!!! info "`value` 字段如果没有冲突的类型转换函数则总是 `MessageChain` 类型"

这样添加了 `List[str]` 与 `List[MessageChain]` 两种类型支持.

### 配合 `Saya` 使用

`#!python from graia.ariadne.message.commander.saya import CommanderBehaviour, CommandSchema`

`CommanderBehaviour` 需要传入一个 `Commander` 实例.

`CommandSchema` 参数与 `Commander.command` 相同.

```py title="示例"
@channel.use(
    CommandSchema(
        "[command|命令] {name}",
        {"option": Arg("[--选项|--option|-O] {option}", str, "")},
    )
)
async def eval_command(name: str, option: str):
    ...
```

!!! graiax "社区文档相关章节: [链接](https://graiax.cn/guide/commander.html)"
