# 消息链工具

## Formatter

`Formatter` 的用法与 `string.Formatter` 差不多, 只不过是给 `MessageChain` 用的.

从 `graia.ariadne.message.formatter` 导入 `Formatter`.

之后直接 `Formatter(template_string).format(...)` 即可.

注意 `format` 方法只支持 `Element`, `MessageChain`, `str` 三种类型参数.

=== "示例"

    ```py
    Formatter("{name} {type} {version} {0}").format(
        MessageChain.create(Plain("bars"), At(111111)),
        name="pog",
        type=Plain("coroutine"),
        version=MessageChain.create(Plain("3.2.1"), At(87654321)),
    )
    ```

=== "结果"

    ```py
    MessageChain(
        [
            Plain(text='pog coroutine 3.2.1',),
            At(target=87654321,),
            Plain(text=' bars',),At(target=111111,),
        ],
    )
    # <MessageChain> len=4
    ```

## Component

`Component` 是一个 `Decorator` 类, 可以方便的保留消息链中的某些部分.

从 `graia.ariadne.message.component` 导入 `Component`.

我们重载了它的 `__class_getitem__` 方法使其可以通过 `Component[T_Types:T_Time]` 的特殊切片形式实例化.

像这样:

```py
@broadcast.receiver(...)
async def reply(msg: MessageChain = Component[(Plain, Image): 2], ...):
    assert len(msg) <= 2
    assert msg.onlyContains(Plain, Image)
    ...
```

或者你也可以自定义过滤函数:

```py
def e_filter(e: Element) -> bool:
    if isinstance(e, Plain):
        if not e.text.startswith("test"):
            return False
    return True

@broadcast.receiver(...)
async def reply(msg: MessageChain = Component[e_filter, 5], ...):
    assert len(msg) <= 5
    assert all(i.text.startswith("test") for i in msg if isinstance(i, Plain))
    ...
```

如你所见, `Component` 有以下实例化形式:

=== "直接实例化"

    ```py
    c = Component(e_filter, match_time)
    ```

=== "切片实例化"

    ```py
    c = Component[e_filter:match_time]
    ```

    !!! info "提示"

        这里 `match_time` 是可选的.

        像这样:

        ```py
        c = Component[e_filter]
        ```

`e_filter` 可为以下形式:

-   `Type[Element] `
-   `Iterable[Type[Element]]`
-   签名为 `(Element) -> bool` 的函数.

`match_time` 为一个 `int`, 代表总匹配次数.

!!! graiax "社区文档相关章节: [链接](https://graiax.cn/make_ero_bot/tutorials/8_huaji.html)"