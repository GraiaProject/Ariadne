# 消息链: 基础

## 为什么是消息链?

QQ 消息并不只是纯文本, 也不只是单一类型的消息. 文本中可以夹杂着图片, At 某人等多种类型的消息.

mirai 为了处理富文本消息, 采用了消息链 (Message Chain)这一方式.

消息链可以看作是一系列元素 (Element) 构成的列表. 消息组件表示消息中的一部分, 比如纯文本 `Plain`, At 某人 `At` 等等.

关于可用的元素, 参看 [API 文档][graia.ariadne.message.element].

## 消息链用法

### 构造消息链

构造消息链时, 建议采用 `MessageChain.create()`.

支持使用以下方法构造.

=== "基础"

    ```py
    message_chain = MessageChain.create([AtAll(), Plain("Hello World!")])
    ```

=== "使用 `str` 代替 `Plain`"

    ```py
    message_chain = MessageChain.create([AtAll(), "Hello World!"])
    ```

=== "省略 `[ ]`"

    ```py
    message_chain = MessageChain.create(AtAll(), "Hello World!")
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
for element in message_chain: ...
```

### 比较

可以使用 `==` 运算符比较两个消息链是否相同.

```py
another_msg_chain = MessageChain([AtAll(), Plain("Hello World!")])
assert message_chain == another_msg_chain
```

### 检查子链

可以使用 `in` 运算检查消息链中：

1. 是否有某个消息组件.
2. 是否有某个类型的消息组件.
3. 是否有某子字符串.
4. 是否有某个消息链. (From **0.4.2** )

```py
AtAll in message_chain

At(app.account) in message_chain

'Hello' in message_chain

MessageChain([AtAll(), "Hello World!"]) in message_chain
```

消息链的 `has` 方法和 `in` 等价.

你可以使用 `onlyContains` 方法检查消息链是否只有某些元素类型.

还可以使用 `find_subchain` 方法寻找可能的消息链子链起始点.

```py
assert message_chain.findSubChain(MessageChain(["Hello"])) == [0]
```

### 索引与切片

消息链对索引操作进行了增强.以元素类型为索引, 获取消息链中的全部该类型的消息组件.

```py
assert message_chain[Plain] == [Plain("Hello World!")]
```

以 `类型, 数量` 为索引, 获取前 **至多** 多少个该类型的元素.

```py
assert message_chain[Plain, 1] == [Plain("Hello World!")]
```

以 `下标` 为索引, 获取对应下标的元素.

```py
assert message_chain[0] == Plain("Hello World!")
```

以 `切片对象` 为索引, 相当于调用 `message_chain.subchain()`.

!!! note "注意"

    这个方法会在 [进阶](/advance/msg-chain/#subchain) 篇中细讲.

消息链的 `get` 方法和索引操作等价.

```py
assert message_chain.get(Plain) == [Plain("Hello World!")]
```

消息链的 `get` 方法可指定第二个参数 `count`, 相当于以 `类型, 数量` 为索引.

```py
assert message_chain.get(Plain, 1) == message_chain[Plain, 1]
```

### 获取元素

在 `MessageChain` 对象上, 有以下几种获取元素的方式:

`getFirst(T_Element)` 获取第一个类型为 `T_Element` 的元素.
`get(T_Element)` 获取所有类型为 `T_Element` 的元素, 聚合为列表.
`getOne(T_Element, index)` 获取第 `index` 个类型为 `T_Element` 的元素。
`get(T_Element, count)` 获取前 `count` 个类型为 `T_element` 的元素, 聚合为列表.

### 连接与复制

可以用 `+` 连接两个消息链, 用 `*` 复制消息链.

```py
assert MessageChain(['Hello World!']) + MessageChain(['Goodbye World!']) == MessageChain([Plain("Hello World!"), Plain("Goodbye World!")])
assert MessageChain(['Hello World!']) * 2 == MessageChain([Plain("Hello World!"), Plain("Hello World!")])
```

### 其他

除此之外, 消息链还支持很多 `list` 拥有的操作, 比如 `index` 和 `count`.

```py
message_chain = MessageChain([AtAll(), "Hello World!"])
assert message_chain.index(Plain) == 0
assert message_chain.count(Plain) == 1
```

还有继承于 `str` 的 `startswith`, `endswith`, `removeprefix`, `removesuffix`, `replace` 方法, 将在 [进阶篇](/advance/msg-chain) 中讲到.

## 多媒体元素

相信你在 `docstring` 与函数签名的辅助下, 能够很快掌握 `Plain` `At` `AtAll` 三种元素类型.

接下来将介绍继承自 `MultimediaElement` 的多媒体元素: `Image` `FlashImage` `Voice`.

### 实例化

你可以通过以下方式自行实例化多媒体元素:

-   从`Mirai API HTTP` 缓存的图片构造: 传入完整 `id` (不是 uuid)
-   从网络图片构造: 传入 `url`
-   从 `bytes` 字节对象构造: 通过 `data_bytes` 传入 `bytes` 包装的二进制数据.
-   从 `base64` 字符串构造: 传入 `base64` 作为二进制存储.
-   从本地文件构造: 传入 `path` 并以 **当前工作目录** 读入二进制数据.

!!! note "提示: 传入的 `path` 会自动被立即提取出二进制数据. 所以不要想着先传 path 再写文件."

### 获取二进制

你可以通过 `get_bytes()` 异步方法获取多媒体元素的二进制数据.

!!! info "提示"

    通过 base64 存储的多媒体元素也可通过本方法取出二进制数据.

    网络图片的二进制数据会在下载后被存储于 `base64` 属性内作为缓存.

### 图片类型转换

可以通过对 `FlashImage` 与 `Image` **实例** 使用 `toImage` `fromImage` `toFlashImage` `fromFlashImage` 方法进行两种图片类型转换.

### 等价性比较

多媒体元素之间的相等比较需要以下条件:

-   类型相同 (也就是说 `Image` 与 `FlashImage` **必定不等**)
-   以下属性中任意一个相等
    -   base64 (data_bytes)
    -   uuid (剔除了 "/" "{}" 等用于区分图片类型的符号后得到)
    -   url

!!! graiax "社区文档相关章节"

    [总览](https://graiax.cn/guide/message_chain.html)

    [多媒体元素](https://graiax.cn/guide/multimedia_message.html)

    [文件发送](https://graiax.cn/guide/file_operation.html)

    [合并转发](https://graiax.cn/guide/forward_message.html)

如果你只是想对 `Ariadne` 有个粗略的了解, 并着手开始编写自己的 QQ bot, 相信这些知识已经足够.
如果你想进一步挖掘 `Ariadne` 的 `MessageChain` 特性, 请看 [进阶篇](/advance/msg-chain) .
