# 配置相关

这里是 `Ariadne` 的 `__init__()` 签名:

```python hl_lines="8-13"
def __init__(
    self,
    connect_info: Union[Adapter, MiraiSession],
    *,
    loop: Optional[AbstractEventLoop] = None,
    broadcast: Optional[Broadcast] = None,
    max_retry: int = -1,
    chat_log_config: Optional[Union[ChatLogConfig, Literal[False]]] = None,
    use_loguru_traceback: Optional[bool] = True,
    use_bypass_listener: Optional[bool] = False,
    await_task: bool = False,
    disable_telemetry: bool = False,
    disable_logo: bool = False,
):
```

### chat_log_config

这个部分是用于控制 Ariadne 的 聊天日志的.

设置为 `False` 即可禁用聊天日志输出.

你可以从 `graia.ariadne.model` 导入 `ChatLogConfig`, 进行更细致的控制.

通过对 `ChatLogConfig` 传入 `log_level` `*_message_log_format` 可以控制聊天日志的记录级别与日志的格式.

### use_loguru_traceback

`Graia Framework` 默认使用 [`traceback`](https://docs.python.org/zh-cn/3/library/traceback.html) 中的
[`traceback.print_exc()`](https://docs.python.org/zh-cn/3/library/traceback.html#traceback.print_exc) 函数输出执行中的异常追踪.

但是其无法直接记录异常至日志中, 且异常回溯有时候并不直观, 导致难以调试.

设置 `use_loguru_traceback` 后, `Ariadne` 会调用 `util.inject_loguru_traceback()` 替换
[`traceback.print_exception()`](https://docs.python.org/zh-cn/3/library/traceback.html#traceback.print_exception) 与
[`sys.excepthook()`](https://docs.python.org/zh-cn/3/library/sys.html#sys.excepthook) 从而获得对异常输出的完全控制权.

### use_bypass_listener

以下代码在 `Graia Broadcast` 的正常流程中不能正常运作,
因为其默认事件分发器只支持原事件 (`listening_event is posted_event`:

```python
@bcc.receiver(MessageEvent)
async def reply(app: Ariadne, event: MessageEvent):
    await app.sendMessage(event, MessageChain.create("Hello!"))
```

设置 `use_bypass_listener` 后, `Ariadne` 会通过 `inject_bypass_listener` 支持子事件解析 (事件透传).

### max_retry

`Ariadne` 默认会尝试无限重启 `Adapter`,
设置 `max_retry` 可以确保在 **连续至少** `max_retry` 次连接失败后自动退出 `daemon` (前提是你使用 `Ariadne.lifecycle()`)

### disable_telemetry

设置为 `True` 后即会禁用启动时的版本检测.

!!! example "你可以在根文件的 TELEMETRY_LIST 下查看检查了哪些包的版本."

### disable_logo

设置为 `True` 后即会禁用启动时的 logo 打印.
