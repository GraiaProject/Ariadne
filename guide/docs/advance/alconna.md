# Alconna - Command Analysis

## 前言
> 阅读本章节前，你需要掌握Ariadne的基础用法


# QuickStart

``` python
import asyncio
from graia.broadcast import Broadcast
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend, MiraiSession
from graia.ariadne.message.parser.alconna import (
    AlconnaParser,
    Alconna,
    Arpamar,
    Option,
    AnyStr,
)  # 必须从这里导入AnyStr，不能从typing中导入

loop = asyncio.get_event_loop()
broadcast = Broadcast(loop=loop)
app = Ariadne(
    MiraiSession(
        host="http://localhost:8080", verify_key="qaq1940QAQ", account=2595201156
    ),
    broadcast=broadcast,
)


ddd = Alconna(
    headers=["#"],  # 命令头
    command="点歌",  # 命令主体
    options=[Option("歌名", song_name=AnyStr), Option("歌手", singer_name=AnyStr)],  # 可选参数
)


@app.broadcast.receiver(FriendMessage, dispatchers=[AlconnaParser(alconna=ddd)])
async def friend_message_listener(app: Ariadne, friend: Friend, arpamar: Arpamar):
    if arpamar.has("歌名"):
        await app.sendFriendMessage(
            friend, MessageChain.create(Plain(arpamar.get_option_first_value("歌名")))
        )
    if arpamar.has("歌手"):
        await app.sendFriendMessage(
            friend, MessageChain.create(Plain(arpamar.get_option_first_value("歌手")))
        )


loop.run_until_complete(app.lifecycle())

```

## 执行这段代码后，向你的bot发送 ``` #点歌 歌名 test 歌手 test ```

## 你会看到

![Example](../images/alconna.png)

## 用法
通过阅读Alconna的签名可以得知，Alconna支持四大类参数：
 - `headers` : 呼叫该命令的命令头，一般是你的机器人的名字或者符号，与command至少有一个填写. 例如: /, !
 - `command` : 命令名称，你的命令的名字，与headers至少有一个填写
 - `options` : 命令选项，你的命令可选择的所有option,是一个包含Subcommand与Option的列表
 - `main_argument` : 主参数，填入后当且仅当命令中含有该参数时才会成功解析



### Option
> 参数类型
>  | 参数名称 | 参数类型 | example |
>  | -------- | -------- |  ------- |
>   | name | 参数名称 | test |
>   | args | 参数可选值 |  test=AnyStr |
> example: Option("参数名称", test=AnyStr)


### Subcommand
> 子命令类型
>   | 参数名称 | 参数类型 | example |
>   | -------- | -------- | ------- |
>   | name | 参数名称 | test |
>   | args | 参数可选值 | List[Option]  |
>  example: Subcommand("参数名称", List[Option])

解析时，先判断命令头(即 headers + command),再判断options与main argument, 这里options与main argument在输入指令时是不分先后的

