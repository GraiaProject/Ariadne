# 更改日志

## 0.5.0

### 添加

- 添加了内置 `Console` ([#41](https://github.com/GraiaProject/Ariadne/issues/41))
- 添加了新的消息链解析工具—— `Alconna` ([#37](https://github.com/GraiaProject/Ariadne/issues/37))

### 改动

- 现在可以接收 `Broadcast` 与 `Adapter` 实例了
- 可以构造转发消息了
- 可以禁用 `WebsocketAdapter` 的心跳包的 log了
- `ArgumentMatch` 支持类型匹配了
- 新的启动与停止 `Ariadne` 的方法
- `Adapter` 的停止过程更安全了 ([#30](https://github.com/GraiaProject/Ariadne/issues/30), [#65](https://github.com/GraiaProject/Ariadne/issues/65))
- 可以更好的获取示例所辖账号了([#31](https://github.com/GraiaProject/Ariadne/issues/31))
- 提升 `Twilight` 的性能 ([#44](https://github.com/GraiaProject/Ariadne/issues/44))
- `sendNudge`（发送戳一戳）现在更灵活了 ([#47](https://github.com/GraiaProject/Ariadne/issues/47))
- 向 `ParallelExecutor` 添加 `to_thread` 与 `to_process` ([#50](https://github.com/GraiaProject/Ariadne/issues/50))
- 将 `graia.ariadne.message.parser.pattern` 的所有内容移到 `Literature` 与 `Twilight` 模块里 ([#53](https://github.com/GraiaProject/Ariadne/issues/53))
- 添加 `ParamMatch` 并拓展 `Sparkle.__getitem__` ([#57](https://github.com/GraiaProject/Ariadne/issues/57))
- 添加 `space` 参数与 `SpacePolicy` 以替代 `preserve_space` ([#59](https://github.com/GraiaProject/Ariadne/issues/59))
- `Ariadne.uploadFile` 支持指定文件名 ([#66](https://github.com/GraiaProject/Ariadne/issues/66))

### 修复

- `Ariadne.uploadImage` 出错 ([#43](https://github.com/GraiaProject/Ariadne/issues/43))
- `async_exec` 相关 ([#50](https://github.com/GraiaProject/Ariadne/issues/50))
- `Queue.get` 任务退出时没被 `await` ([#51](https://github.com/GraiaProject/Ariadne/issues/51))
- 自动用 `repr()` 转义 log 中发送的消息 ([#58](https://github.com/GraiaProject/Ariadne/issues/58))
- `Adapter` 不会自动重连 ([#60](https://github.com/GraiaProject/Ariadne/issues/60))
- `NudgeEvent` 接收陌生人的戳一戳出错 ([#63](https://github.com/GraiaProject/Ariadne/issues/63))

### Breaking Changes

- `Ariadne.request_stop` -> `Ariadne.stop`
- `Ariadne.wait_for_stop` -> `Ariadne.join`
