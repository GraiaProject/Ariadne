# 参数传递

在事件解析函数中使用类型提示是 `Graia Framework` 相较于其他 Python QQ SDK 最大的亮点.

!!! info "提示"

    如果你不知道类型提示是什么, 请参看 [这里](https://docs.python.org/zh-cn/3/library/typing.html)

在 [快速开始](../../quickstart/) 一节中, 我们使用了这样的写法来处理好友的消息:

```python
@broadcast.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne, friend: Friend):
    ......
```

这是因为我们需要为参数添加 **类型注解** , 才能获得对应的数据.

上面的例子中, `app: Ariadne` 的 `Ariadne` 部分, 与 `friend: Friend` 的 `Friend` 部分是不可以省略的. 用不到的参数, 可以省略. 比如说, 如果你在 `friend_message_lister` 中, 没有用到 `friend` 参数, 那么就可以写成这样:

```python
@broadcast.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne):
    ......
```

下面列出 Ariadne 中所有基于 `MessageEvent` 的消息可接受的参数类型.

所有类型:

-   `T_EventType`: 你所监听的事件类型, 如 `FriendMessage`, `GroupMessage` 等.
-   `Ariadne`: 通过 `app = Ariadne(...)` 创建的 Ariadne 对象.
-   `Broadcast`: 当前 `graia.broadcast.Broadcast` 实例.
-   `AbstractEventLoop`: 当前事件循环.
-   `Adapter`: 当前 `Adapter` 实例.
-   `MessageChain`: 消息链对象, 将在 [下一章](../msg-chain) 介绍.
-   `Source`: 消息元数据对象, 包括发送时间等信息.

此外, 对于以下事件类型还可接受这些参数:

-   `FriendMessage`
    -   `Friend`: 发送者.
-   `GroupMessage`
    -   `Member`: 发送者.
    -   `Group`: 发送者所在的群组.
-   `TempMessage`
    -   `Member`: 发送者.
    -   `Group`: 通过哪个群发起的临时消息.
-   `OtherClientMessage`
    -   `Client`: 发送者.
-   `StrangerMessage`
    -   `Stranger` 发送者.

!!! graiax "社区文档相关章节: [链接](https://graiax.cn/guide/other_event.html)"

!!! info "提示"

    参数解析功能, 是由 `Dispatcher` 机制来实现的, 可阅读 [`Dispatcher` 文档](https://autumn-psi.vercel.app/docs/broadcast/basic/dispatcher) , 以简要了解其原理.

    在进阶教程中, 我们将要介绍的 [`Twilight`](../../advance/twilight/) , 也使用了 `Dispatcher` 机制.
