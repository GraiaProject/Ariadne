# 使用 Channel

推荐在模块开头使用 `channel = Channel.current()` 后, 使用以下方法:

- `channel.name(str)`: 定义插件名字.
- `channel.author(str)`: 定义插件的作者 (你自己).
- `channel.description(str)`: 定义插件描述 (通常是用法).

## channel.use

这是 `Channel` 的核心方法. 也是 `Saya module` 与其他部分交互的首选途径.

### 用法

你需要一个 `Schema` 对象, 之后

```py
@channel.use(SchemaObject)
async def fetch(...):
    ...
```

即可. 与其他函数定义方式相同.

有以下几个 `Schema`.

- `ListenerSchema`: 需要 `BroadcastBehaviour`, 相当于使用 `bcc.receiver`.
- `SchedulerSchema`: 需要 `GraiaSchedulerBehaviour`, 相当于使用 `scheduler.schedule`.
