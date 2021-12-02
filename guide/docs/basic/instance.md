# Ariadne 实例

!!! note "引言"

    `Ariadne` 的实例方法大多继承自 `Mixin`.
    这允许 `Ariadne` 方便的拓展各种方法.
    当你不知道 `Ariadne` 为什么可以做到这些事时, 看看这些 `Mixin` 吧.

## 生命周期管理

`launch()` 用于启动 `Ariadne` 实例, `stop()` 用于停止 `Ariadne` 实例.

`lifecycle()` 通过 `await self.daemon_task`, 即等待 `Adapter` 的守护任务, 达到封装 `launch()` 与 `wait_for_stop()` 的目的.

!!! note "提示"

    其实 `Ariadne` 也可以作为 `async context manager` 使用.

    在 `__aenter__` 中执行 `launch()`, 在 `__aexit__` 中执行 `wait_for_stop()`.

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

`Ariadne`通过一个只读属性`account`来帮助用户获取当前机器人实例的 QQ 号

```python
# 0.4.6以前
account = app.adapter.mirai_session.account
# 0.4.6之后
account = app.account
```

## 停止实例

在 `0.4.7` 之前, `Ariadne` 的实例无法正常等待 `Adapter` 完成任务后再退出.

在 `0.4.7` 中, 我们重新设计了 `Ariadne` 实例的生命周期.

现在你通过在监听器中 `await app.request_stop()` 并在主函数中 `await app.wait_for_stop()` 应该可以安全的关闭 `Ariadne`.

当然, 在主函数中使用 `await app.lifecycle()` 永远是最佳实践.
