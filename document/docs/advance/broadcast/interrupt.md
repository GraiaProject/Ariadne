# Interrupt - 中断

有时你可能需要进一步获取信息以处理.

比如这样:

<div>
<ul>
 <li class="chat right">/kick 12345678</li>
 <li class="chat left"> 请发送 "/confirm" 确认</li>
 <li class="chat right">/confirm</li>
 <li class="chat left">已将 BadUser(12345678) 踢出</li>
</ul>
</div>

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

!!! warning "注意"

    `waiter()` 函数内填充的参数 **不能通过手工传入**,
    而应该通过与 `bcc.receiver()` 一样的参数分派机制进行自动填充.

    注意 `ListeningEvent` 不能使用 `"GroupMessage"` 这种字符串形式,
    而要导入具体事件之后填入.

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

## 它是怎么运作的?

`Interrupt` 创建的 `Waiter` 对象很像 `asyncio.Future`, 是基于回调的设计.

在 `inc.wait()` 时, 会创建一个临时的事件监听器, 等待 `Waiter` 成功执行事件处理, 并将其处理结果传回 `inc.wait()` 的调用者.

也就是说, `inc.wait` 判断, 处理的是 **"下一个"** 消息 / 事件.

!!! info "额外消息"

    你可以利用 `asyncio.wait_for()` 来进行带有超时的监听.

    当其 `Waiter` 包装的函数返回非 `None` 值时, `InterruptControl.wait` 方法将该返回值作为执行结果返回.

    你可以进一步处理返回值.

    使用循环可以接受多个消息的参数输入.

!!! note "提示"

    通过往 `Waiter.create_using_function` 添加事件类型可以同时监听多个事件,

    或者直接传入 `list(graia.ariadne.util.gen_subclass(EventType))` 一口气接受所有子事件.

## 几个例子

`Ariadne` 并没有 `Application` 中封装好的 `Waiter` 包装器, 不过这里有一些你可以跟着做的示例.

=== "验证群"

    ```py
    @Waiter.create_using_function([GroupMessage])
    async def validate_group(group: Group):
        if group.id == 1234567: # 随便你怎么处理, 反正成立时返回一个不为 None 的就行.
            return True
    ```

=== "验证好友"

    ```py
    @Waiter.create_using_function([FriendMessage])
    async def validate_friend(friend: Friend):
        if friend.id == 7654321: # 随便你怎么处理, 反正返回一个不为 None 的就行.
            return True
    ```


就这么多, 接下来我们将介绍在 `FastAPI` 中广泛运用的特性: 依赖注入 (`Depend`).
