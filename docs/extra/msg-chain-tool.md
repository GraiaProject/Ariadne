# 消息链工具

## Formatter

`Formatter` 的用法与 `string.Formatter` 差不多, 只不过是给 `MessageChain` 用的.

从 `graia.ariadne.message.formatter` 导入 `Formatter`.

之后直接 `Formatter(template_string).format(...)` 即可.

注意 `format` 方法只支持 `Element`, `MessageChain`, `str` 三种类型参数.

=== "示例"

    ```py
    Formatter("{name} {type} {version} {0}").format(
        MessageChain(Plain("bars"), At(111111)),
        name="pog",
        type=Plain("coroutine"),
        version=MessageChain(Plain("3.2.1"), At(87654321)),
    )
    ```

=== "结果"

    ```py
    MessageChain(
        [
            Plain(text='pog coroutine 3.2.1',),
            At(target=87654321,),
            Plain(text=' bars',),
            At(target=111111,),
        ],
    )
    # <MessageChain> len=4
    ```

!!! graiax "社区文档相关章节: [链接](https://graiax.cn/guide/formatter.html)"
