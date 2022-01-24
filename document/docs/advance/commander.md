# Commander - 便捷的命令触发系统

## 在开始之前

现在 `Ariadne` 的命令解析实现方式异常丰富.

- 最简单的指令解析: `DetectPrefix` 与 `DetectSuffix`, 看 [上一章](./base-parser.md)

- 最简洁易用 / 基于 `pydantic` `BaseModel` 的指令处理器: `Commander`

- 基于正则表达式的解析 / 容错性高且易于编写的处理器: [`Twilight`](./twilight.md)

- 支持子命令解析 / 基于 dict 的高度定制解析: [`Alconna`](./alconna/quickstart.md)

按照你的需求, 选择最适合你的处理器.

## 开始使用

`Commander` 有着比较简单的语法, 但是需要手动触发.

```py
from graia.ariadne.message.commander import Commander, Slot, Arg

bcc: Broadcast = ...

cmd = Commander(bcc)

@cmd.command(
    "[luckperm|lp|perm] user {0} permission set {1|permission} {2}",
    {
        "user": Slot(0), # 自动推断: type=At
        "permission": Slot(1, type=str),
        "value": Slot(2, type=bool, default=True), # default=True 表明可选
        "verbose": Arg("[-v|--verbose]", type=bool, default=False)
    },
    [Dispatcher_1, ...],
    [Decorator_1, ...],
)
async def set_permission(user: At, permission: str, value: bool, verbose: bool):
    ...

@bcc.receiver(GroupMessage)
async def post_cmd(chain: MessageChain):
    cmd.execute(chain)
```

<!-- TODO: 需要重新施工-->

## `command` 字段

本字段允许使用以下三种标记符号, 均用空格分开

- 纯文本 (`text`): 完全匹配该文本

- 选择匹配 (`[text1|text2|text3]`): 从 `|` 分开的文本中任意匹配 (`text1` / `text2` / `text3`)

- 占位符 (`{PL_1|123}`): 占位符为 `|` 分开的别名, 符合数字的会自动被转成 `int`. (本示例的占位符: `"PL_1"` / `123`)

## Slot

`Slot` 有四个参数: `slot`, `type`, `default`, `default_factory`.

`slot` 代表它要引用的占位符: 如上文中的 `"PL_1"`, `123` 等.

`type` 代表接收的类型, 可以从装饰函数的类型标注自动推断.

!!! warning "注意: `type` 值优先于函数的类型标注."

`default` 与 `default_factory` 任选其一, 代表默认值 (或其工厂函数), 表明该 `Slot` 为可选.

!!! warning "注意, 此时要求该 `Slot` 对应的占位符为 **最后一个字段** ."

## Arg

`Arg` 有四个参数: `pattern`, `type`, `default`, `default_factory`.

`pattern` 的格式与 `command` 中的格式相同, 但是有且仅有首个字段为纯文本/选择匹配, 后面的占位符也不能有别名, 不能为可选项.

`type` 同样可从装饰函数的类型标注自动推断, 但是:

    - 在 `pattern` 无占位符时, 为 `bool`, 通过 `default` 自动反转值.

    - 在 `pattern` 仅有一个占位符时, 可为任意可识别类型 / `BaseModel` 子类, 会自动被转化为合适的 `BaseModel` 子类.

    - 否则, 你需要手动传入继承于 `BaseModel` 的类型, 该类型接受 `pattern` 中占位符命名的字段. (可参见 `Arg 中使用的 BaseModel`)

`default` 与 `default_factory` 必选其一, 代表默认值 (或其工厂函数).

!!! warning "注意"

    多个占位符时,

    `list` 会逐个填入占位符名称并传给 `type` 模型.

    `dict` 会直接传给 `type` 模型.
    
    `BaseModel` 实例保持不变.

    例如, 对于:

    ```py
    class AModel(BaseModel):
        _ = validator("*", pre=True, allow_reuse=True)(chain_validator) 

        value: str
        level: int
    
    Arg("-a {value} {level}", type=AModel, default=default_val)
    ```

    `default_val` 以下样式等价:

    - `["default", 0]`

    - `{"value": "default", "level": 0}` 

    - `AModel(value="default", level=0)`

比如:

`{"v_level": Arg("[-v|--verbose] {level}", type=int, default=0)}` 会对 `v_level: int` 传入一个 `int` 值.

## Arg 中使用的 BaseModel

`Commander` 模块提供了一个方便的 `chain_validator` 函数, 用于方便 `Arg` 中使用 `BaseModel`.

这个函数可作为 `pydantic.validator` 参数使用以辅助类型转换 (`Commander` 会向 `BaseModel` 传入 `MessageChain` 值).

对于 `Arg("[--example|-e] {value} {level}", type=DerivedModel, default={"value": "default", "level": 0})`

```py
class DerivedModel(BaseModel):

    _ = validator("*", pre=True, allow_reuse=True)(chain_validator) 

    value: str

    level: int
```

关于如何拓展 `validator` , 参见 [`pydantic 文档`](https://pydantic-docs.helpmanual.io/usage/validators/)

!!! error "警告"

    你创建的 `BaseModel` 子类永远不应继承于 `AriadneBaseModel`,

    否则 `Commander` 无法将其与 `MessageChain` `Element` 等类型区分.