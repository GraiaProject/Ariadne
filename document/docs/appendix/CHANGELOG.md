# 更改日志

## 0.5.0

### 添加

添加内置 `Console` ([#41](https://github.com/GraiaProject/Ariadne/issues/41)).

添加 `Alconna` 支持 ([#37](https://github.com/GraiaProject/Ariadne/issues/37)).

### 改动

现在可以接收 `Broadcast` 与 `Adapter` 实例了.

提升 `Twilight` 性能 ([#44](https://github.com/GraiaProject/Ariadne/issues/44)).

`sendNudge` 现在更灵活了 ([#47](https://github.com/GraiaProject/Ariadne/issues/47)).

向 `ParallelExecutor` 添加 `to_thread` 与 `to_process` ([#50](https://github.com/GraiaProject/Ariadne/issues/50))

将 `graia.ariadne.message.parser.pattern` 的所有内容移到 `literature` 与 `twilight` 模块里. ([#53](https://github.com/GraiaProject/Ariadne/issues/53))

添加 `ParamMatch` 并拓展 `Sparkle.__getitem__` ([#57](https://github.com/GraiaProject/Ariadne/issues/57))

添加 `space` 参数与 `SpacePolicy` 以替代 `preserve_space` ([#59](https://github.com/GraiaProject/Ariadne/issues/59))

`Ariadne.request_stop` -> `Ariadne.stop`

`Ariadne.wait_for_stop` -> `Ariadne.join`

### 修复

[#50](https://github.com/GraiaProject/Ariadne/issues/50) `async_exec` 相关

[#51](https://github.com/GraiaProject/Ariadne/issues/51) `Queue.get` 任务退出时没被 `await`

[#58](https://github.com/GraiaProject/Ariadne/issues/58) 自动用 `repr()` 转义发送的消息

[#63](https://github.com/GraiaProject/Ariadne/issues/63) `NudgeEvent` 接收陌生人的戳一戳