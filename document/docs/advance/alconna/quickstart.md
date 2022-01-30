# 快速开始

!!! warning "关于本模块"

    本模块由 `RF-Tar-Railt` 维护,
    `BlueGlassBlock` 仅进行了针对 `Ariadne` 的封装, 本模块余下部分从 `Alconna wiki` 复制并修改而来.

```python
from arclet.alconna import Args, Option
from graia.ariadne.message.parser.alconna import (
    AlconnaDispatcher,
    Alconna,
    Arpamar
)
# example: !点歌 <歌名> --歌手 <歌手名>
#
#                                  主参数: <歌名>      选项名: --歌手  选项别名: -s  选项参数: <歌手名>     
music = Alconna.from_string("!点歌 <song_name:str>", "--歌手|-s <singer_name:str>")

@app.broadcast.receiver(FriendMessage, dispatchers=[AlconnaDispatcher(alconna=music)])
async def friend_message_listener(app: Ariadne, friend: Friend, arpamar: Arpamar):
    if arpamar.matched:
        if arpamar.has("song_name"):
            await app.sendFriendMessage(
                friend, MessageChain.create("歌名是 ", arpamar.song_name) # or use arpamar.get("song_name")
            )
        if arpamar.has("singer_name"):
            await app.sendFriendMessage(
                friend, MessageChain.create("歌手是 ", arpamar.singer_name) # or use arpamar.get("singer_name")
            )
```

执行这段代码后，向你的 bot 发送 `!点歌 歌名 大地 歌手 Beyond` 试试.

<div>
<ul>
 <li class="chat right">!点歌 歌名 大地 歌手 Beyond</li>
 <li class="chat left">歌名是 大地</li>
 <li class="chat left">歌手是 Beyond</li>
</ul>
</div>

## 用法

通过阅读 Alconna 的签名可以得知，Alconna 支持四大类参数：

-   `headers` : 呼叫该命令的命令头，一般是你的机器人的名字或者符号，与 command 至少有一个填写. 例如: /, !
-   `command` : 命令名称，你的命令的名字，与 headers 至少有一个填写
-   `options` : 命令选项，你的命令可选择的所有 option,是一个包含 Subcommand 与 Option 的列表
-   `main_args` : 主参数，填入后当且仅当命令中含有该参数时才会成功解析

解析时，先判断命令头(即 headers + command ),再判断 options 与 main args , 这里 options 与 main args 在输入指令时是不分先后的

假设有个 Alconna 如下:

```python
Alconna(
    headers=["/"],
    command="name",
    options=[
        Subcommand(
            "sub_name",
            Option("sub_opt", sub_opt_arg="sub_arg"), 
            sub_main_arg="sub_main_arg"
        ),
        Option("opt", opt_arg="opt_arg")
    ]
    main_args="main_args"
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

## 参数标注

`AlconnaDispatcher` 可以分配以下几种参数:

-   `Alconna`: 使用的 `Alconna` 对象.
-   `Arpamar`: `Alconna` 生成的数据容器.
-   `AlconnaProperty`: 在 `name` 上进行此标注等价于进行 `arpamar.get(name)`.

## 与 Twilight 对比

`Twilight` 偏重于对消息链的正则化处理,

而 `Alconna` 偏重于对参数的各种形式解析, 不限于消息链 (更像 `argparse` 模块).

另一点, `Alconna`的功能相对复杂, 不太适合初识消息解析的用户.

如果你想要 `argparse` 中各种特别 `Action` (如 `append`) 的原生支持, 可能 `Twilight` 会更好编写.

同时, `Twilight` 是基于对象的参数处理器, 在类型补全上更完备.

但是 `Alconna` 有子命令的支持, 且性能占优.

总之, 根据自己的需要, 选择合适的工具.

## 下一步

`Ariadne` 只对 `Alconna` 进行了简单的封装, 接下来你可以访问其 [文档](https://arcletproject.github.io/docs/alconna/tutorial) 进一步了解用法.
