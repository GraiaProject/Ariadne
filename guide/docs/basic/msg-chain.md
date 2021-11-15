# 消息链: 基础

## 为什么是消息链?

QQ 消息并不只是纯文本, 也不只是单一类型的消息. 文本中可以夹杂着图片, At 某人等多种类型的消息.

mirai 为了处理富文本消息, 采用了消息链 (Message Chain)这一方式.

消息链可以看作是一系列元素 (Element) 构成的列表. 消息组件表示消息中的一部分, 比如纯文本 `Plain`, At 某人 `At` 等等.

关于可用的元素, 参看 [API 文档](https://graiaproject.github.io/Ariadne/message/element.html).

## 消息链用法

### 构造消息链

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

### 消息链的字符串表示

使用 `message_chain.asDisplay()` 获取消息链的字符串表示.字符串表示的格式类似于手机 QQ 在通知栏消息中的格式, 例如图片会被转化为 `[图片]`, 等等.

### 消息链持久化

使用 `message_chain.asPersistentString()` 和 `MessageChain.fromPersistentString()` 可以尽量无损地持久化与恢复消息链,
使用 `binary=True` 可以保存图片等多媒体元素的二进制数据.

!!! info "提示"

    如果要持久化二进制数据, 可以先调用 `message_chain.download_binary()`.

### 遍历

可以使用 for 循环遍历消息链中的消息组件.

```py
for element in message_chain:
    print(repr(component))
```

### 比较

可以使用 `==` 运算符比较两个消息链是否相同.

```py
another_msg_chain = MessageChain([
    {
        "type": "AtAll"
    }, {
        "type": "Plain",
        "text": "Hello World!"
    },
])
print(message_chain == another_msg_chain)
'True'
```

### 检查子链

可以使用 `in` 运算检查消息链中：

1. 是否有某个消息组件.
2. 是否有某个类型的消息组件.
3. 是否有某子字符串.

```py
if AtAll in message_chain:
    print('AtAll')
if At(bot.qq) in message_chain:
    print('At Me')
if MessageChain([At(bot.qq), Plain('Hello!')]) in message_chain:
    print('Hello!')
if 'Hello' in message_chain:
    print('Hi!')
```

消息链的 `has` 方法和 `in` 等价.

```py
if message_chain.has(AtAll):
    print('AtAll')
```

### 索引与切片

消息链对索引操作进行了增强.以消息组件类型为索引, 获取消息链中的全部该类型的消息组件.

```py
plain_list = message_chain[Plain]
'[Plain("Hello World!")]'
```

以 `类型, 数量` 为索引, 获取前至多多少个该类型的消息组件.

```py
plain_list_first = message_chain[Plain, 1]
'[Plain("Hello World!")]'
```

以 `下标` 为索引, 获取底层对应下标的元素.

```py
first = message_chain[0]
'[Plain("Hello World!")]'
```

以 `切片对象` 为索引, 相当于调用 `message_chain.subchain()`.

!!! note "注意"

    这个方法会在进阶篇中细讲.

消息链的 `get` 方法和索引操作等价.

```py
plain_list_first = message_chain.get(Plain)
'[Plain("Hello World!")]'
```

消息链的 `get` 方法还可指定第二个参数 `count`, 这相当于以 `类型, 数量` 为索引.

```py
plain_list_first = message_chain.get(Plain, 1)
# 这等价于
plain_list_first = message_chain[Plain, 1]
```

### 连接与复制

可以用加号连接两个消息链.

```py
MessageChain(['Hello World!']) + MessageChain(['Goodbye World!'])
# 返回 MessageChain([Plain("Hello World!"), Plain("Goodbye World!")])
```

可以用 `*` 运算符复制消息链.

```py
MessageChain(['Hello World!']) * 2
# 返回 MessageChain([Plain("Hello World!"), Plain("Hello World!")])
```

### 其他

除此之外, 消息链还支持很多 list 拥有的操作, 比如 `index` 和 `count`.

```py
message_chain = MessageChain([
    AtAll(),
    "Hello World!",
])
message_chain.index(Plain)
# 返回 0
message_chain.count(Plain)
# 返回 1
```
