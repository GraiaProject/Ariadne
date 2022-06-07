# Console - 内建实时控制台

!!! warning "提前说明"

    `Console` 的底层 `prompt-toolkit` 并不完备...... <span class="curtain">所以别拿着 prompt-toolkit 的 bug 来找我</span>

!!! error "注意"

    `0.7.0` 后 `Console` 与 `richuru` 同时使用并不理想.

`Console` 是可以与 `Ariadne` 分离的, 不过它默认会与 `Ariadne` 一起启动与停止,
你可以通过在实例化时传入 `listen_launch`, `listen_shutdown` 来控制这个行为.

## 实例化

```py
def __init__(
    self,
    broadcast: Broadcast,
    prompt: Union[Callable[[], str], AnyFormattedText] = "{library_name} {graia_ariadne_version}>",
    *,
    r_prompt: Union[Callable[[], str], AnyFormattedText] = "",
    style: Optional[Style] = None,
    extra_data_getter: Iterable[Callable[[], Dict[str, Any]]] = (),
    replace_logger: bool = True,
    listen_launch: bool = True,
    listen_shutdown: bool = True,
    ) -> None:
        """初始化控制台."""
```


- **broadcast** (`Broadcast`): 事件系统.

- **prompt** (`AnyFormattedText, optional`): 输入提示, 可使用 `f-string` 形式的格式化字符串.
默认为 `{library_name} {graia_ariadne_version}>`.

- **r_prompt** (`AnyFormattedText, optional`): 右侧提示, 可使用 `f-string` 形式的格式化字符串. 默认为空.

- **style** (`Style`, `optional`): 输入提示的格式, 详见 `prompt_toolkit` 的介绍.

- **extra_data_getter** (`Iterable[() -> Dict[str, Any], optional`): 额外的 `Callable`, 用于生成 prompt 的格式化数据.

- **replace_logger** (`bool, optional`): 是否尝试替换 loguru 的 0 号 handler (`sys.stderr`) 为 `StdoutProxy`. 默认为 `True`.

- **listen_launch** (`bool, optional`): 是否监听 Ariadne 的 ApplicationLaunched 事件并启动自身, 默认为 `True`.

- **listen_shutdown** (`bool, optional`): 是否监听 Ariadne 的 ApplicationShutdowned 事件并停止自身, 默认为 `True`.

你可以看到这样配置后, 随着终端的启动, 你可以看到类似这样的效果:

```bash
Ariadne A.B.C>
```

你可以在这里自由输入, 而且你可以看到日志记录并没有混在一起.

!!! info "这个在你尝试使用多线程实现 `Console` 时就会发生."

```log
                _           _
     /\        (_)         | |
    /  \   _ __ _  __ _  __| |_ __   ___
   / /\ \ | '__| |/ _` |/ _` | '_ \ / _ \
  / ____ \| |  | | (_| | (_| | | | |  __/
 /_/    \_\_|  |_|\__,_|\__,_|_| |_|\___|
Ariadne version: A.A.A
Broadcast version: B.B.B
Saya version: C.C.C
Scheduler version: D.D.D
| INFO     | graia.ariadne.app:launch:1356 - Launching app...
| DEBUG    | graia.ariadne.app:daemon:1264 - Ariadne daemon started.

Ariadne A.A.A>
```

你可以看到, 在按下 `Ctrl + C` 后, `Console` 也会自动将尚未完成的输入行变灰并退出.

接下来, 让我们注册 `Console` 命令处理器.

## 注册命令处理器

有以下两种风格的注册方式

=== "类 broadcast.receiver"

    ```py
    con = Console(...)

    @console.register([Dispatcher_1, ...], [Decorator_1, ...])
    def resp_1(command: str): ...

    @console.register([Dispatcher_1, ...])
    async def resp_2(chain: MessageChain): ...
    ```

=== "Saya"

    ```py title="main.py"
    from graia.ariadne.console import Console
    from graia.ariadne.console.saya import ConsoleBehaviour

    saya = ...
    con = Console(...)
    saya.install_behaviours(ConsoleBehaviour(con))
    ```

    ```py title="some_module.py"
    from graia.ariadne.console.saya import ConsoleSchema

    channel = ...

    @channel.use(ConsoleSchema([Dispatcher_1, ...], [Decorator_1, ...]))
    def resp_1(command: str): ...

    @channel.use(ConsoleSchema([Dispatcher_1, ...]))
    async def resp_2(chain: MessageChain): ...
    ```

`register` 方法与 `ConsoleSchema` 的签名均为 `(dispatchers: List[Dispatcher] = None, decorators: List[Decorator] = None) -> Callable[[T_Callable], T_Callable]`

## 可分派的参数

通过 `register` 或 `ConsoleSchema` 注册的 `Callable` 可获得以下参数:

- `Broadcast`: 当前 `Broadcast` 实例.

- `Console`: 当前 `Console` 实例.

- `AbstractEventLoop`: 当前事件循环

- `command - str`: 必须以 `command: str` 的形式标注, 输入的实际字符串.

- `MessageChain`: 将 `command` 转换为纯文本 `MessageChain` 的产物, 使大部分 `Dispatcher / Decorator` 可被使用.

- (`Ariadne`): 若有 `Ariadne` 实例在运行则可被分派.

## 手动 prompt

`Console` 一个值得注意的地方是它的每个处理函数是被单独等待执行的. (按照添加从早到晚的顺序)

也就是说, 你可以通过 `raise PropagationCancelled` 来阻断剩下的处理函数执行.

同时, 你可以通过获取 `Console` 实例完成以下操作.

```py
@con.register([Twilight.from_command("!stop")])
async def stop(app: Ariadne, con: Console):

    input = await con.prompt("Are you sure to exit?", "<Y/N>", Style.from_dict({...}))

    if input.lower().startswith("y"):
        await app.stop()
```

效果大致是这样的: (<span class="curtain">可惜没有彩色显示</span>)

```log
Ariadne A.A.A>!stop
Are you sure to exit?y                                                   <Y/N>

| INFO     | graia.ariadne.console:stop:199 - Stopping console...
| DEBUG    | graia.ariadne.app:daemon:1296 - Ariadne daemon stopped.
| INFO     | graia.ariadne.app:daemon:1300 - Stopping Ariadne...
| INFO     | graia.ariadne.app:daemon:1315 - Posting Ariadne shutdown event...
```

`Console.prompt` 签名如下: (注意, 实例化时的 `prompt` 参数与 prompt 方法的 `l_prompt` 参数名不同, 但用途相同. 这是有意为之的.)

```py
async def prompt(
    self,
    l_prompt: Optional[AnyFormattedText] = None,
    r_prompt: Optional[AnyFormattedText] = None,
    style: Optional[Style] = None,
) -> str:
    """向控制台发送一个输入请求, 异步

    Returns:
        str: 输入结果
    """
```

- **l_prompt** (`AnyFormattedText, optional`): 左输入提示, 可使用 `f-string` 形式的格式化字符串.
默认为 `{library_name} {graia_ariadne_version}>`. 注意为 `l_prompt` .

- **r_prompt** (`AnyFormattedText, optional`): 右侧提示, 可使用 `f-string` 形式的格式化字符串. 默认为空.

- **style** (`Style, optional`): 输入提示的格式, 详见 `prompt_toolkit` 的介绍.

!!! graiax "社区文档相关章节: [链接](https://graiax.cn/guide/console.html)"
