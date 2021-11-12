# 消息链: 基础

## 为什么是消息链?

QQ 消息并不只是纯文本, 也不只是单一类型的消息. 文本中可以夹杂着图片, At 某人等多种类型的消息.

mirai 为了处理富文本消息, 采用了消息链 (Message Chain)这一方式.

消息链可以看作是一系列元素 (Element) 构成的列表. 消息组件表示消息中的一部分, 比如纯文本 `Plain`, At 某人 `At` 等等.

关于可用的元素, 参看 [API 文档](https://graiaproject.github.io/Ariadne/message/element.html).

## 构造消息链

构造消息链时, 建议采用 `MessageChain.create()`.

支持使用以下方法构造.

=== "基础"

    ```py
    message_chain = MessageChain([
        AtAll(),
        Plain("Hello World!"),
    ])
    ```

=== "使用 `str` 代替 `Plain`"

    ```py
    message_chain = MessageChain([
        AtAll(),
        "Hello World!",
    ])
    ```

=== "省略 `[ ]`"

    ```py
    message_chain = MessageChain(
        AtAll(),
        "Hello World!",
    )
    ```

## 元素类型一览
