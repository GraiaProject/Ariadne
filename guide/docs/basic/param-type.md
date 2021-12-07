# 参数及类型

!!! info "提示"

    如果你不知道类型提示是什么, 请参看 [这里](https://docs.python.org/zh-cn/3/library/typing.html)

在[快速开始](/quickstart/)一节中, 我们使用这样的写法来处理好友的消息:

```python
@bcc.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne, friend: Friend):
    ......
```

我们需要为参数添加 **类型注解** , 才能获得对应的数据上面的例子中,  `app: Ariadne` 的 `Ariadne` 部分, 与 `friend: Friend` 的 `Friend` 部分是不可以省略的. 用不到的参数, 可以省略. 比如说, 如果你在 `friend_message_lister` 中, 没有用到 `friend` 参数, 那么就可以写成这样:

```python
@bcc.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne):
    ......
```

下面列出 Ariadne 中所有可以接收的消息类型, 以及处理该类型消息时可用的参数:

```python
from graia.ariadne.model import Client, Friend, Group, Member
from graia.ariadne.event.message import FriendMessage, GroupMessage, MessageEvent, OtherClientMessage, StrangerMessage, TempMessage
from graia.ariadne.message.element import Source
from graia.ariadne.message.chain import MessageChain


@bcc.receiver(MessageEvent)
async def friend_message_listener(app: Ariadne, message: MessageChain, source: Source):
    pass


@bcc.receiver(FriendMessage)
async def friend_message_listener(app: Ariadne, message: MessageChain, source: Source, friend: Friend):
    pass


@bcc.receiver(GroupMessage)
async def friend_message_listener(app: Ariadne, message: MessageChain, source: Source, group: Group, member: Member):
    pass


@bcc.receiver(TempMessage)
async def friend_message_listener(app: Ariadne, message: MessageChain, source: Source, group: Group, member: Member):
    pass


@bcc.receiver(OtherClientMessage)
async def friend_message_listener(app: Ariadne, message: MessageChain, source: Source, client: Client):
    pass


@bcc.receiver(StrangerMessage)
async def friend_message_listener(app: Ariadne, message: MessageChain, source: Source, sender: Friend):
    pass
```

其中 `app: Airadne` 参数, 即为前文通过 `app = Ariadne(......)` 创建的 Ariadne 对象; `message: MessageChain` 参数, 我们将在[消息链: 基础](/basic/msg-chain/)一节中进行介绍.

!!! info "提示"

    参数解析功能, 是由 `Dispatcher` 机制来实现的, 可阅读 [`Dispatcher` 的文档](https://autumn-psi.vercel.app/docs/broadcast/basic/dispatcher) , 以简要了解其原理.
 
    在进阶教程中, 我们将要介绍的 [`Twilight`](/advance/twilight/) , 也使用了 `Dispatcher` 机制.
