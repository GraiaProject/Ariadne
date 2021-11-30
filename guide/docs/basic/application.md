# Ariadne 实例

!!! note "引言"

    `Ariadne` 的实例方法大多继承自 `Mixin`.
    这允许 `Ariadne` 方便的拓展各种方法.
    当你不知道 `Ariadne` 为什么可以做到这些事时, 看看这些 `Mixin` 吧.

## 生命周期管理


`launch()` 用于启动 `Ariadne` 实例, `stop()` 用于停止 `Ariadne` 实例.

`lifecycle()` 通过 `await self.daemon_task`, 即等待 `Adapter` 的守护任务, 达到封装 `launch()` 与 `stop()` 的目的.

!!! note "提示"

    其实 `Ariadne` 也可以作为 `async context manager` 使用.

    在 `__aenter__` 中执行 `launch()`, 在 `__aexit__` 中执行 `stop()`.

???+ note "对于 Graia Application 用户"

    请使用 `loop.run_until_complete(app.lifecycle())` 代替 `app.launch_blocking()`.

## 交互方法

`Ariadne` 与 QQ 进行交互的方法遵循以下原则:

- 使用 `camelCase` 驼峰命名.
- 使用 `谓词 + 名词` 命名.
- 注: 获取数据的方法统一以 `get` 开头.
- 为 `async` 异步函数.

其他的信息你应该可以从 `doc string` 里得到.

!!!info "对于 Graia Application 用户"

    你可以直接使用 `app.sendMessage(sender_or_event, message, ...)` 发送信息.

## 获取实例所管账号(0.4.6+)

`Ariadne`通过一个只读属性`account`来帮助用户获取当前机器人实例的QQ号
```python
# 0.4.6以前
account = app.adapter.mirai_session.account
# 0.4.6之后
account = app.account
```