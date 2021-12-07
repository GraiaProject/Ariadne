# 自定义消息链处理器

有时, 前面介绍的基础消息链处理器与 `Twilight` 消息链处理器, 都不能满足我们的需求. 目前, Ariadne 尚无统一的权限管理系统, 也没有提供过滤群号与好友的接口. 此时, 就需要我们自己处理.

实现自定义消息链处理器, 最简单的方法, 是使用 `Depend()` 构造一个 `Headless Decorator`.

首先, 我们需要实现一个异步函数. 它可以接收[与消息处理器相同的参数](/basic/param-type/). 如果我们想对群号进行检查, 让机器人只响应某个群中的消息, 可以这样写：

```python
async def check_group(group: Group):
    if group.id != 12345678:
        raise ExecutionStop()
```

这里, 触发的 `ExecutionStop` 异常, 会结束 Ariadne 对消息的处理, 也就是说, 除了群号为 `12345678` 以外的群里有消息时, 机器人就不会响应了.

首先导入 `Decorator`:

```python
from graia.broadcast.builtin.decorators import Depend
```

接下来, 我们用 `Depend(check_group)` 创建一个 `Decorator` , 并把它传入 `bcc.receiver` 中:

```python
@bcc.receiver(GroupMessage, decorators=[Depend(check_group)])
async def map(app: Ariadne, group: Group):
    await app.sendMessage(group, MessageChain.create([Plain("I'm here!")]))
```

运行机器人进行测试, 此时机器人只会响应群号为 12345678 的群里的消息.

`Decorator` 也可以配合前面提到的基础消息链处理器, 还有 `Twilight`, 一起使用:

```python
@bcc.receiver(
    GroupMessage,
    dispatchers=[Twilight(Sparkle([RegexMatch("地图|路线图")]))],
    decorators=[Depend(check_group)],
)
async def map(app: Ariadne, group: Group):
    await app.sendMessage(group, MessageChain.create([Image(path="data/map.jpg")]))
```
