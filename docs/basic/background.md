# 后台任务

`Ariadne` 没有自带 `add_background_task` 之类的玩意, 不过我们可以自己 ~~手搓~~ 造一个.

首先, 从 `graia.ariadne.event.lifecycle` 导入 `ApplicationLaunched` 与 `ApplicationShutdowned`

监听 `ApplicationLaunched` , 利用这个监听启动你的后台任务.

监听 `ApplicationShutdowned` , 利用这个清理你的后台任务.

!!! note "提示"

    如果你想要使用多个账号的话, 注意 `ApplicationLaunched` 和 `ApplicationShutdowned` 事件绑定的是 **默认账号**.

    每个账号在 `Ariadne` 启动与停止时都会分发一次 `AccountLaunch` 和 `AccountShutdown` 事件.

    使用 `Ariadne.current(special_id)` 可以获取指定账号的 `Ariadne` 实例.


```py
bg_tsk: Optional[Task] = None

@broadcast.receiver(ApplicationLaunched)
async def start_background(loop: AbstractEventLoop):
    global bg_tsk
    if not bg_tsk:
        bg_tsk = loop.create_task(whatever_coroutine(...))


@broadcast.receiver(ApplicationShutdowned)
async def stop_background():
    global bg_tsk
    if bg_tsk:
        # bg_tsk.cancel() # 取不取消随你, 但不要留到 Ariadne 生命周期外
        await bg_tsk
        bg_tsk = None
```

当然, 你可以这样封装.

```py
def add_background_task(app: Ariadne, async_func: Callable[[...], Awaitable], *args, **kwargs):
    bg_tsk: Optional[Task] = None

    @app.broadcast.receiver(ApplicationLaunched)
    async def start_background(loop: AbstractEventLoop):
        if not bg_tsk:
            bg_tsk = loop.create_task(async_func(*args, **kwargs))


    @broadcast.receiver(ApplicationShutdowned)
    async def stop_background():
        if bg_tsk:
            bg_tsk.cancel() # 取不取消随你, 但不要留到 Ariadne 生命周期外
            await bg_tsk
            bg_tsk = None
```

其实, 你在监听 `ApplicationLaunched` 事件时可以直接扔一个死循环, 通过判断 `Ariadne.launch_manager.status` 决定什么时候停止运行.

像这样:

```py
from graia.ariadne.model import AriadneStatus

@broadcast.receiver(ApplicationLaunched)
async def background(app: Ariadne):
    while Ariadne.launch_manager.status.stage in ("prepare", "blocking"):
        ...
        await asyncio.sleep(0.01) # 循环里至少要有一个 async 操作
```

注意: 最好随着 `Ariadne` 生命周期一起清理后台任务, 否则我们无法担保你的事件循环会不会炸 (无法 Ctrl + C 退出等).

!!! note "提示"

    和其他监听器一样, 你的 `ApplicationLaunched` 监听器只会被运行一次, 所以最好将其作为一个循环运行.
