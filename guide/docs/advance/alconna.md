# Alconna - 来自 Cesloi 的命令分析工具


!!! info "前言"

    在这之前，你应该已经熟悉了 Ariadne 的基础部分

# QuickStart

``` python
from graia.ariadne.message.parser.alconna import (
    AlconnaParser,
    Alconna,
    Arpamar,
    Option,
    AnyStr,
)  # 必须从这里导入 AnyStr，不能从 typing 中导入


# example:   !点歌 歌名 大地 歌手 Beyond
ddd = Alconna(
    headers=["!"],  # 命令头
    command="点歌",  # 命令主体
    options=[  # 可选参数
        Option("歌名", song_name=AnyStr),
        Option("歌手", singer_name=AnyStr)
    ], 
)


@app.broadcast.receiver(FriendMessage, dispatchers=[AlconnaParser(alconna=ddd)])
async def friend_message_listener(app: Ariadne, friend: Friend, arpamar: Arpamar):
    if arpamar.matched:
        if arpamar.has("歌名"):
            await app.sendFriendMessage(
                friend, MessageChain.create("歌名是 ",arpamar.get("歌名").get("song_name")) # or use arpamar.get_option_first_value("歌名")
            )
        if arpamar.has("歌手"):
            await app.sendFriendMessage(
                friend, MessageChain.create("歌手是 ",arpamar.get("歌手").get("singer_name")) # or use arpamar.get_option_first_value("歌手")
            )
```

## 执行这段代码后，向你的 bot 发送 ``` !点歌 歌名 大地 歌手 Beyond ```

## 你会看到

![Example](../images/alconna.png)

## 用法
通过阅读 Alconna 的签名可以得知，Alconna 支持四大类参数：
 - `headers` : 呼叫该命令的命令头，一般是你的机器人的名字或者符号，与 command 至少有一个填写. 例如: /, !
 - `command` : 命令名称，你的命令的名字，与 headers 至少有一个填写
 - `options` : 命令选项，你的命令可选择的所有 option,是一个包含 Subcommand 与 Option 的列表
 - `main_argument` : 主参数，填入后当且仅当命令中含有该参数时才会成功解析

解析时，先判断命令头(即 headers + command ),再判断 options 与 main argument , 这里 options 与 main argument 在输入指令时是不分先后的

假设有个 Alconna 如下:
```python
Alconna(
    headers=["/"],
    command="name",
    options=[
        Subcommand("sub_name",Option("sub-opt", sub_arg="sub_arg"), args=sub_main_arg),
        Option("opt", arg="arg")
        ]
    main_argument="main_argument"
)
```
则它可以解析如下命令:
```
/name sub_name sub-opt sub_arg opt arg main_argument
/name sub_name sub_main_arg opt arg main_argument
/name main_argument opt arg
/name main_argument
```
解析成功的命令的参数会保存在analysis_message 方法返回的 `Arpamar` 实例中
