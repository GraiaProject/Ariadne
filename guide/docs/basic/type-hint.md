# 类型提示

在事件解析函数中使用类型提示进行对象分发是 `Graia Framework` 相较于其他 Python QQ SDK 最大的亮点.

!!! warning "注意"

    如果你不知道类型提示是什么, 请参看 [这里](https://docs.python.org/zh-cn/3/library/typing.html)

通常来说, 你可以写出这样的代码:

```py
@bcc.receiver(GroupMessage)
async def parse(group: Group, msg: MessageChain, sender: Member):
    ...
```

而不用这样:

```py
@bcc.receiver(GroupMessage)
async def parse(event: GroupMessage):
    group = event.sender.group
    msg = event.messageChain
    sender = event.sender
```

而这一切, 都拜底层的 [`Dispatcher`](https://autumn-psi.vercel.app/docs/broadcast/basic/dispatcher) 所赐.

当然, 这些 `Dispatcher` 的原理有些晦涩, 你现在无需理解.

你只需要记住, 你在函数中定义的所有参数都需要标注类型, 你标注了什么类型, 就会传入什么类型. 这样既优雅又易懂.

同时, 借助后面介绍的 `Twilight` `Alconna` 等自定义的 `Dispatcher`, 你将可以获取更多信息.
