# Ariadne 总览

!!! note "引言"

    `Ariadne` 的实例方法大多继承自 `Mixin`.
    这允许 `Ariadne` 方便的拓展各种方法.
    当你不知道 `Ariadne` 为什么可以做到这些事时, 看看这些 `Mixin` 吧.

## 关于使用 "模型" 的提示

`Group` `Friend` `Member` `Stranger` 四个类型支持 `__int__` 协议获取其 `id` 属性.

也就是说, `int(group)` 等价于 `group.id` .

`Group` `Friend` `Member` 上还有 `getInfo` `modifyInfo` `getProfile` `modifyAdmin` `getConfig` `modifyConfig` 等方便方法.

## 某些事件的额外方法

[`RequestEvent`](https://github.com/GraiaProject/Ariadne/blob/master/src/graia/ariadne/event/mirai.py#L773)
带有一些额外方法, 如 `accept` `reject` `ignore` 等, 直接在其上使用 `await` 即可.

## 生命周期管理

`launch()` 用于启动 `Ariadne` 实例, `stop()` 用于停止 `Ariadne` 实例.

`lifecycle()` 通过 `await self.daemon_task`, 即等待 `Adapter` 的守护任务, 达到封装 `launch()` 与 `wait_for_stop()` 的目的.

如果你不需要额外的 `asyncio` 操作, 那么 `app.launch_blocking()` 应该足以满足你的需要, 因为它封装了 `launch()`, 并在捕获 `KeyboardInterrupt` 时自动 `wait_for_stop()`.

!!! note "提示"

    其实 `Ariadne` 也可以作为 `async context manager` 使用.

    在 `__aenter__` 中执行 `launch()`, 在 `__aexit__` 中执行 `wait_for_stop()`.

## 交互方法

`Ariadne` 与 QQ 进行交互的方法遵循以下原则:

- 使用 `camelCase` 驼峰命名.
- 使用 `谓词 + 名词` 命名.
- 注: 获取数据的方法统一以 `get` 开头.
- 为 `async` 异步函数.

其他的信息你应该可以从 `doc string` 里得到.

## 获取实例所管账号

`Ariadne` 通过一个只读属性 `account` 来帮助用户获取当前机器人实例的 QQ 号

```python
account = app.account
```

## 停止实例

现在你通过在监听器中 `await app.stop()` 并在主函数中 `await app.join()` 应该可以安全的关闭 `Ariadne`.

当然, 在主函数中使用 `await app.lifecycle()` 或 `app.launch_blocking()` 永远是最佳实践.

## 方便的消息发送方法 - sendMessage

`sendMessage` 有一个限制: 只能从传入对象推断 (不能直接传入 `int` 格式的 `target`)

但是它可以智能地从传入对象推断: `Friend` `Group` `Member` `MessageEvent` 这四个都是合适的传入对象.

`Friend` 发送好友消息, `Group` 发送群组消息, **而 `Member` 发送临时私聊消息**.

`MessageEvent` 则会推断是 `GroupMessage`, `FriendMessage` 还是 `TempMessage`, 并自动发给对应的对象.

同时, 在向 `target` 传入消息事件时, `quote` 可以简单地传入 `True` 以达到引用回复的效果.

`quote` 也接受 `Source` 元素.

### sendMessage 的 action

`sendMessage` 可以携带一个 `action` 参数,
它是一个 `graia.ariadne.typing.SendMessageAction` 对象, 需要实现以下方法:

- `param`: 处理传入的数据并进行加工 (可用于自动携带 `At` 等消息元素)

- `result`: 成功发送时调用, 作为最终返回用户的数据.

- `exception`: 发送时发生异常则会调用, 作为最终返回用户的数据.

`Ariadne` 在 `graia.ariadne.util.send` 内建了以下 `SendMessageAction`, 直接传入这些类即可.

- `Strict`: 发生异常时自动引发. (默认)

- `Bypass`: 发生异常时返回异常对象, 注意异常重生的问题.

- `Ignore`: 发生异常时返回 `None`.

- `Safe`: 在第一次尝试失败后先移除 `quote`,
之后每次失败时按顺序替换元素为其 `asDisplay`: `AtAll`, `At`, `Poke`, `Forward`, `MultimediaElement`
若最后还是失败 (`AccountMuted` 等), 则会引发原始异常 (通过传入 `ignore` 决定)

下面是示例:

```py
from graia.ariadne.util.send import Strict, Bypass, Ignore, Safe

act = Strict or Bypass or Ignore or Safe or Safe(ignore=False) or Safe(ignore=True) # 看你怎么选择

await app.sendMessage(origin, message_chain, action=act)
```

### 设置默认 action

`Ariadne` 实例的默认 `action` 是 `Strict`, 你可以通过 `Ariadne.default_send_action` 属性透明地修改.