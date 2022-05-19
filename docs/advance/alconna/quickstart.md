# Alconna - 功能强大的命令解析器

!!! warning "关于本模块"

    本模块由 `RF-Tar-Railt` 维护,
    `BlueGlassBlock` 仅进行了针对 `Ariadne` 的封装, 本模块余下部分从 `Alconna wiki` 复制并修改而来.

## 快速开始

以下将直观展示`Alconna`的使用方法:

```python
from arclet.alconna import AlconnaString, Arpamar
from arclet.alconna.graia import AlconnaDispatcher
# example: !点歌 <歌名> 歌手 <歌手名>
music = AlconnaString(
    "!点歌 <song_name:str>  #在XXX中搜索歌名", # 主参数: <歌名>
    "歌手|-s <singer_name:str> #指定歌手"  # 选项名: 歌手  选项别名: -s  选项参数: <歌手名>
)
@app.broadcast.receiver(FriendMessage, dispatchers=[AlconnaDispatcher(alconna=music, help_flag='reply')])
async def friend_message_listener(app: Ariadne, friend: Friend, result: Arpamar):
    await app.sendFriendMessage(friend, MessageChain.create("歌名是 ", result.song_name))
    if result.singer_name:
        await app.sendFriendMessage(friend, MessageChain.create("歌手是 ", result.singer_name))
```

执行这段代码后，向你的 bot 发送 `!点歌 大地 -s Beyond` 试试.

<div>
<ul>
 <li class="chat right">!点歌 大地 -s Beyond</li>
 <li class="chat left">歌名是 大地</li>
 <li class="chat left">歌手是 Beyond</li>
 <li class="chat right">!点歌 --help</li>
 <li class="chat left">!点歌 &lt;song_name&gt;<br>在XXX中搜索歌名<br>可用的选项有:<br>&#35; 指定歌手<br>  -s, 歌手 &lt;singer_name&gt;</li>
</ul>
</div>

## 创建 Alconna

假设我们编写了这样的代码:

```python
from arclet.alconna import Alconna, Args, Option
...

alconna = Alconna("指令", Args.foo[str], options=[Option("my选项")])
```

这个命令说明我们需要匹配一个内容为 "指令 something"的消息(其中 `something` 必须是 `str` 类型), 并把 "something" 赋予参数名 "foo"; 该指令可以使用 "my选项" 这个命令选项

而后另有4种构造方式, 可以满足不同使用者的需求:
- koishi-like: 以类似 `koishi` 中指令创建的方式创建 `Alconna`
- format: 以类似f-string的格式创建 `Alconna`
- click-like: 以类似 `click` 中指令创建的方式创建 `Alconna`
- fire-like: 以类似 `python-fire` 中指令创建的方式创建 `Alconna`

具体使用方法请参考 `Alconna` 的文档.

## 结构

通过阅读 Alconna 的签名可以得知，Alconna 支持四大类参数:
- `command` : 命令名称，你的命令的名字，与 headers 至少有一个填写
- `main_args` : 主参数，填入后当且仅当命令中含有该参数时才会成功解析
- `headers` : 呼叫该命令的命令头，一般是你的机器人的名字或者符号，与 command 至少有一个填写. 例如: /, !
- `options` : 命令选项，你的命令可选择的所有 option,是一个包含 Subcommand 与 Option 的列表

解析时，先判断命令头(即 headers + command ),再判断 options 与 main args , 这里 options 与 main args 在输入指令时是不分先后的

若有如下命令:

```python
Alconna(
    command="name",
    main_args="main_args",
    headers=["/"],
    options=[
        Subcommand(
            "sub_name",
            [Option("sub_opt", "sub_arg")],
            args="sub_main_arg"
        ),
        Option("opt", "opt_arg")
    ],
)
```

则它可以解析以下所有消息:

```
/name sub_name sub_opt sub_arg sub_main_arg opt arg main_args
/name main_args sub_name sub_main_arg opt arg
/name opt arg main_args
/name main_args
```

解析成功的命令的参数会保存在 parse 方法返回的 `Arpamar` 实例中

## 使用 `AlconnaDispatcher`

您可以在 `Ariadne` 中使用 `AlconnaDispatcher` 来帮助解析命令.

### 参数标注

`AlconnaDispatcher` 可以分配以下几种参数:

- `Alconna`: 使用的 `Alconna` 对象.
- `Arpamar`: `Alconna` 生成的数据容器.
- `AlconnaProperty`: `AlconnaDispatcher` 返回的特殊对象, 可以获取:
    - `help_text`: 可能的帮助信息
    - `result`: `Arpamar`
    - `source`: 原始事件
- 其他类型: 在 `name` 上进行此标注等价于`arpamar.all_matched_args.get(name)`

### 特殊事件

当`AlconnaDispatcher`的`reply_help`为`False`时, 其会向bcc广播一个`AlconnaHelpMessage`事件

该事件可获取的参数如下:
- `help_string`(str): 可能的帮助信息
- `alconna` (Alconna): 该帮助信息对应的命令
- `sender`, `messageChain`, `app`, ...: 从源消息事件中可获取的所有参数

## 与 `Saya` 的使用

`Alconna-Graia` 在 0.0.12 更新了 `saya` 相关部分, 包括 `AlconnaSchame` 与 `AlconnaBehaviour`

```python
...
from arclet.alconna.graia.saya import AlconnaSchema, AlconnaBehaviour
from arclet.alconna.graia.dispatcher import AlconnaDispatcher, AlconnaProperty
from arclet.alconna import Alconna, command_manager
from graia.saya.builtins.broadcast import ListenerSchema, BroadcastBehaviour
from graia.saya import Saya, Channel
...
saya = Saya(broadcast=bcc)
saya.install_behaviours(
  BroadcastBehaviour(broadcast=bcc)
  AlconnaBehaviour(broadcast=bcc, manager=command_manager)
)
...

channel = Channel.current()


@channel.use(AlconnaSchema("test"))
@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[AlconnaDispatcher(alconna=Alconna("test", "foo:int"))]
    )
)
async def _(app: Ariadne, res: AlconnaProperty):
    ...

@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=Alconna("test1", "foo:int"))))
@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def _(app: Ariadne, res: AlconnaProperty):
    ...

@channel.use(AlconnaSchema.using("test2 <foo:int>"))
@channel.use(ListenerSchema(listening_events=[GroupMessage]))
async def _(app: Ariadne, res: AlconnaProperty):
    ...
```

使用 `AlconnaSchema` 可以避免因为重载模块导致的命令报错

## 配合 AlconnaDuplication

`Alconna` 在 0.7.7 中新增了 `AlconnaDuplication`, 可以用来进行更好的解析提取

```python
...
from arclet.alconna import AlconnaDuplication, ArgsStub, OptionStub
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna import Option, Args
...

class Test(AlconnaDuplication):
  my_args: ArgsStub
  my_option: OptionStub


alc = Alconna("test", Args.foo[int]) + Option("my_option", Args.bar[str])


@app.broadcast.receiver(FriendMessage, dispatchers=[AlconnaDispatcher(alconna=alc)])
async def friend_message_listener(app: Ariadne, friend: Friend, dup: Test):
    print(dup.my_args.first_arg)
    await app.sendFriendMessage(friend, MessageChain.create(dup.my_option.name))
    ...
```

另可以直接传入 `Stub`, 如
```python
...
async def friend_message_listener(app: Ariadne, friend: Friend, my_args: ArgsStub, my_option: OptionStub):
    print(my_args.first_arg)
    await app.sendFriendMessage(friend, MessageChain.create(my_option.name))
    ...
```

## 与 Twilight 对比

`Twilight` 偏重于对消息链的正则化处理,

而 `Alconna` 偏重于对消息链的多样化命令式解析 (更像 `typer` 模块), 并且不限于解析消息链.

如果你想要传统命令式的解析处理 (如`argparse`), 可能 `Alconna` 会更合胃口.

如果你想要 `argparse` 中各种特别 `Action` (如 `append`) 的原生支持, 可能 `Twilight` 会更好编写.

另一点,  `Alconna` 有更好更强大的参数类型解析与子命令的支持, 且魔法较多(迫真), 不太适合初识消息解析的用户.

总之, 根据自己的需要, 选择合适的工具.

## 下一步

`Ariadne` 只对 `Alconna` 进行了简单的封装, 接下来你可以访问其 [文档](https://arcletproject.github.io/docs/alconna/tutorial) 进一步了解用法.

!!! graiax "社区文档相关章节: [链接](https://graiax.cn/guide/alconna.html#alconna)"
