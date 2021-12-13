# 更改日志

## 0.5.0

### 添加

添加 `CHANGELOG`.

添加内置 `Console` ([#41](https://github.com/GraiaProject/Ariadne/issues/41)). (WIP)

添加 `Alconna` 支持 ([#37](https://github.com/GraiaProject/Ariadne/issues/37)).

### 改动

提升 `Twilight` 性能 ([#44](https://github.com/GraiaProject/Ariadne/issues/44)).

`sendNudge` 现在更灵活了 ([#47](https://github.com/GraiaProject/Ariadne/issues/47)).

向 `ParallelExecutor` 添加 `to_thread` 与 `to_process` ([#50](https://github.com/GraiaProject/Ariadne/issues/50))

将 `graia.ariadne.message.parser.pattern` 的所有内容移到 `literature` 与 `twilight` 模块里. ([#53](https://github.com/GraiaProject/Ariadne/issues/53))

### 修复

[#51](https://github.com/GraiaProject/Ariadne/issues/51) `Queue.get` 任务退出时没被 `await`

[#50](https://github.com/GraiaProject/Ariadne/issues/50) `async_exec` 相关
