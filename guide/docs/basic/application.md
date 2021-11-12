# Ariadne 实例

!!! note "引言"

    `Ariadne` 的实例方法大多继承自 `Mixin`.
    这允许 `Ariadne` 方便的拓展各种方法.
    当你不知道 `Ariadne` 为什么可以做到这些事时, 看看这些 `Mixin` 吧.

## 生命周期管理

如你在 [`app.py`](https://github.com/GraiaProject/Ariadne/blob/master/src/graia/ariadne/app.py) 中所见, `Ariadne` 有以下几个方法.

```python
class Ariadne(...):
    async def launch(self): ...
    async def lifecycle(self): ...
    async def stop(self): ...
```

也很容易想到这几个方法的用途:

`launch()` 用于启动 `Ariadne` 实例, `stop()` 用于停止 `Ariadne` 实例.

!!! question "问题"

    但 `lifecycle()` 怎么使用呢?

别急, 让我们看看 `lifecycle()` 的源码.

```python hl_lines="2 8"
async def lifecycle(self):
    await self.launch()
    try:
        if self.daemon_task:
            await self.daemon_task
    except CancelledError:
        pass
    await self.stop()
```

真相大白. **`lifecycle()` 只是对 `launch()` 与 `stop()` 的封装**.

至于为什么要 `await self.daemon_task`, 之后我们会提到.

## 交互方法

`Ariadne` 与 QQ 进行交互的方法遵循以下原则:

- 使用 `camelCase` 驼峰命名.
- 使用 `谓词 + 名词` 命名.
- 注: 获取数据的方法统一以 `get` 开头.
- 为 `async` 异步函数.

其他的信息你应该可以从 `doc string` 里得到. 此处不再赘述.

!!!info "对于 Graia Application 用户"

    你可以直接使用 `app.sendMessage(sender_or_event, message, ...)` 发送信息.

!!!note "提示"

    `MessageChain` 如何使用会在下一节介绍.
