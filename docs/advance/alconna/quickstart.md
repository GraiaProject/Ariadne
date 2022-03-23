# Alconna - 功能强大的命令解析器

!!! warning "关于本模块"

    本模块由 `RF-Tar-Railt` 维护,
    `BlueGlassBlock` 仅进行了针对 `Ariadne` 的封装, 本模块余下部分从 `Alconna wiki` 复制并修改而来.

## 快速开始

以下将直观展示`Alconna`的使用方法:

```python
from arclet.alconna import AlconnaString, Arpamar
from arclet.alconna.graia import AlconnaDispatcher
# example: !点歌 <歌名> --歌手 <歌手名>
music = AlconnaString(
    "!点歌 <song_name:str>  #在XXX中搜索歌名", # 主参数: <歌名>
    "--歌手|-s <singer_name:str> #指定歌手"  # 选项名: --歌手  选项别名: -s  选项参数: <歌手名>
)
@app.broadcast.receiver(FriendMessage, dispatchers=[AlconnaDispatcher(alconna=music, help_flag='reply')])
async def friend_message_listener(app: Ariadne, friend: Friend, result: Arpamar):
    await app.sendFriendMessage(friend, MessageChain.create("歌名是 ", Arpamar.song_name))
    if singer_name:
        await app.sendFriendMessage(friend, MessageChain.create("歌手是 ", Arpamar.singer_name))
```

执行这段代码后，向你的 bot 发送 `!点歌 大地 -s Beyond` 试试.

<div>
<ul>
 <li class="chat right">!点歌 大地 -s Beyond</li>
 <li class="chat left">歌名是 大地</li>
 <li class="chat left">歌手是 Beyond</li>
 <li class="chat right">!点歌 --help</li>
 <li class="chat left">!点歌 &lt;song_name&gt;<br>在XXX中搜索歌名<br>可用的选项有:<br>&#35; 指定歌手<br>  -s, --歌手 &lt;singer_name&gt;</li>
</ul>
</div>

## 结构

通过阅读 Alconna 的签名可以得知，Alconna 支持四大类参数：

-   `headers` : 呼叫该命令的命令头，一般是你的机器人的名字或者符号，与 command 至少有一个填写. 例如: /, !
-   `command` : 命令名称，你的命令的名字，与 headers 至少有一个填写
-   `options` : 命令选项，你的命令可选择的所有 option,是一个包含 Subcommand 与 Option 的列表
-   `main_args` : 主参数，填入后当且仅当命令中含有该参数时才会成功解析

解析时，先判断命令头(即 headers + command ),再判断 options 与 main args , 这里 options 与 main args 在输入指令时是不分先后的

假设有个 Alconna 如下:

```python
Alconna(
    command="name",
    main_args="main_args",
    headers=["/"],
    options=[
        Subcommand(
            "sub_name",
            Option("sub_opt", sub_opt_arg="sub_arg"),
            sub_main_arg="sub_main_arg"
        ),
        Option("opt", opt_arg="opt_arg")
    ],
)
```

则它可以解析如下命令:

```
/name sub_name sub_opt sub_arg sub_main_arg opt arg main_args
/name sub_name sub_main_arg opt arg main_argument
/name main_args opt arg
/name main_args
```

解析成功的命令的参数会保存在 analysis_message 方法返回的 `Arpamar` 实例中

## 创建 Alconna

```python
alconna = Alconna(command="指令", main_args=Args.foo[str], options=[Option("选项")])
```

这里说明我们需要匹配内容为 "指令 something:str"的消息, 并把 "something" 赋予参数名 "foo"; 该指令可以使用 "选项" 这个命令选项

而后另有4种构造方式, 可以满足不同使用者的需求:
- koishi-like: 以类似`koishi`中指令创建的方式创建`Alconna`
- format: 以类似f-string的格式创建`Alconna`
- click-like: 以类似`click`中指令创建的方式创建`Alconna`
- fire-like: 以类型`python-fire`中指令创建的方式创建`Alconna`

## 使用 `AlconnaDispatcher`

您可以在 `Ariadne` 中使用 `AlconnaDispatcher` 来帮助解析命令.

### 参数标注

`AlconnaDispatcher` 可以分配以下几种参数:

- `Alconna`: 使用的 `Alconna` 对象.
- `Arpamar`: `Alconna` 生成的数据容器.
- `AlconnaProperty`: `AlconnaDispatcher` 返回的特殊对象, 可以获取:
    - `origin`: 原始消息链
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

## 与 Twilight 对比

`Twilight` 偏重于对消息链的正则化处理,

而 `Alconna` 偏重于对参数的各种形式解析, 不限于消息链 (更像 `argparse` 模块).

另一点, `Alconna`的功能相对复杂, 不太适合初识消息解析的用户.

如果你想要 `argparse` 中各种特别 `Action` (如 `append`) 的原生支持, 可能 `Twilight` 会更好编写.

同时, `Twilight` 是基于对象的参数处理器, 在类型补全上更完备.

但是 `Alconna` 有更好更强大的参数类型解析与子命令的支持, 且性能占优, 魔法较多(迫真).

总之, 根据自己的需要, 选择合适的工具.

## 下一步

`Ariadne` 只对 `Alconna` 进行了简单的封装, 接下来你可以访问其 [文档](https://arcletproject.github.io/docs/alconna/tutorial) 进一步了解用法.

!!! graiax "社区文档相关章节: [链接](https://graiax.cn/make_ero_bot/tutorials/6_4_alconna.html)"
