# 配置相关

!!!info "注意"

    这里介绍的是 `Ariadne` 的 配置, 而非 `Mirai-API-HTTP` 的.

## 让我们从 "签名" 开始

这里是 `Ariadne` 的 `__init__()` 签名:

```python hl_lines="6-9"
def __init__(
    self,
    broadcast: Broadcast,
    adapter: Adapter,
    *,
    chat_log_config: Optional[Union[ChatLogConfig, Literal[False]]] = None,
    use_loguru_traceback: Optional[bool] = True,
    use_bypass_listener: Optional[bool] = False,
    max_retry: int = -1
): ...
```

`broadcast`, `adapter` 自不必说. 但剩下三个仅关键字参数值得说一下.

让我们来一个个介绍.

### chat_log_config

这个部分是用于控制 Ariadne 的 聊天日志的.

如果你不喜欢启用聊天日志输出, 设置为 `False` 即可.

你可以从 `graia.ariadne.model` 导入 `ChatLogConfig`, 进行更细致的控制.

通过对 `ChatLogConfig` 传入 `log_level` `*_message_log_format` 可以控制聊天日志的记录级别与日志的格式.

### use_loguru_traceback

`Graia Framework` 默认使用 [`traceback`](https://docs.python.org/zh-cn/3/library/traceback.html) 中的
[`traceback.print_exc()`](https://docs.python.org/zh-cn/3/library/traceback.html#traceback.print_exc) 函数输出执行中的异常追踪.

这并没有什么问题, 但是...

- 无法直接记录至日志中.
- 异常回溯有时候并不直观. (尤其是函数调用经过了多个包装器时)

设置 `use_loguru_traceback` 后, `Ariadne` 会调用 `util.inject_loguru_traceback()` 替换
[`traceback.print_exception()`](https://docs.python.org/zh-cn/3/library/traceback.html#traceback.print_exception) 与
[`sys.excepthook()`](https://docs.python.org/zh-cn/3/library/sys.html#sys.excepthook) 从而获得对异常输出的完全控制权.

### use_bypass_listener

你可能想过这样写:

```python
@bcc.receiver(MessageEvent)
async def reply(app: Ariadne, event: MessageEvent):
    await app.sendMessage(event, MessageChain.create("Hello!"))
```

不幸的是, `Graia Broadcast` 的默认事件分发器只支持原事件 (`listening_event is posted_event`).

所以你的代码并不能正常监听到 `FriendMessage`, `GroupMessage` 等子事件.

设置 `use_bypass_listener` 后, `Ariadne` 会通过某些魔法支持子事件解析 (事件透传).

现在, 事件分发就能支持子事件了. (`posted_event is instance of listening event`)

!!! note "提示"

    如果你真的非常关心实现细节, 它在 `util.inject_inject_bypass_listener()` 里.

## max_retry

`Ariadne` 默认会尝试无限重启 `Adapter`,
设置 `max_retry` 可以确保在 **连续至少** `max_retry` 次连接失败后自动退出 `daemon` (前提是你使用 `Ariadne.lifecycle()`)
