# Interrupt - 中断

有时你可能需要进一步获取信息以处理.

比如这样:

```text title="聊天记录"
User -> /kick 12345678
Bot  -> 请发送 "/confirm" 确认
User -> /confirm
Bot  -> 已将 BadUser(12345678) 踢出
```

对于此种交互方式, 我们提供了 `Interrupt` 以支持.

## 开始使用

先进行导入:

```py
from graia.broadcast.interrupt import InterruptControl
from graia.broadcast.interrupt.waiter import Waiter
```

创建 `InterruptControl` 对象:

=== "直接创建"

    ```py
    inc = InterruptControl(broadcast)
    ```

=== "通过 Ariadne.create"

    ```py
    inc = AriadneInstance.create(InterruptControl)
    ```

之后通过函数包装创建 `Waiter`:

```py
@Waiter.create_using_function([ListeningEvent])
def waiter(...):
    # 判断和处理
    if condition:
        return True # 只要不是 None 就会继续执行
```

!!! info "提示"

    经过包装后, `waiter` 函数就变成了一个 `SingleWaiter` 对象.

    可以将 `Waiter.create_using_function` 看作 `Broadcast.receiver`.

    `dispatcher`, `decorator` 等 `Broadcast` 特性是受支持的.

之后在主监听函数中:

```py
@bcc.receiver(ListeningEvent)
async def handler(...):
    ...
    result = await inc.wait(waiter) # 在此处等待
    ...
```

!!! info "额外消息"

    你可以利用 `asyncio.wait_for()` 来进行带有超时的监听.

    当其 `Waiter` 包装的函数返回非 `None` 值时, `InterruptControl.wait` 方法将该返回值作为执行结果返回.

    你可以进一步处理返回值.

    使用循环可以接受多个消息的参数输入.

!!! note "提示"

    通过往 `Waiter.create_using_function` 添加事件类型可以同时监听多个事件,

    或者直接传入 `list(graia.ariadne.util.gen_subclass(EventType))` 一口气接受所有子事件.

就这么多, 接下来我们将介绍在 `FastAPI` 中广泛运用的特性: 依赖注入 (`Depend`).
