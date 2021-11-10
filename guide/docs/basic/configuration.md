# 配置相关

!!!info "注意"

    这里介绍的是 `Ariadne` 的 配置, 而非 `Mirai-API-HTTP` 的.

## 让我们从 "签名" 开始

这里是 `Ariadne` 的 `__init__()` 签名:

```python
    def __init__(
        self,
        broadcast: Broadcast,
        adapter: Adapter,
        *,
        chat_log_config: Optional[Union[ChatLogConfig, Literal[False]]] = None,
        use_loguru_traceback: Optional[bool] = True,
        use_bypass_listener: Optional[bool] = False,
    ):
    ...
```

`broadcast`, `adapter` 自不必说. 但剩下三个仅关键字参数值得说一下.

让我们来一个个介绍.

### chat_log_config

这个部分是用于控制 Ariadne 的 聊天日志的.

如果你不喜欢启用聊天日志保存, 设置为 `False` 即可.

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
[`sys.excepthook()`](https://docs.python.org/zh-cn/3/library/sys.html#sys.excepthook)

从而获得对异常输出的完全控制权.

### use_bypass_listener
