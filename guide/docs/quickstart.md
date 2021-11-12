# 快速开始

## 前言

这里我们假设你已经参照 [ `mirai` ](https://github.com/mamoe/mirai) 和 [ `mirai-api-http` ](https://github.com/mamoe/mirai-api-http)
的 README,

启动了你的 `mirai-console` , 同时也安装了最新版本的 `mirai-api-http` 插件.

!!!important "重要"

    如果你使用时开发库出现了错误, 应先检查是否是 `Graia Framework` 的错误,
    确认之后, 请在我们的 [GitHub Issues](https://github.com/GraiaProject/Ariadne/issues) 处汇报你的错误,
    我们会尽快处理问题

!!! error "注意"

    本 快速开始 文档假设你已有 [`Python 3.7+`](https://docs.python.org/zh-cn/3/) 与 [`asyncio`](https://docs.python.org/zh-cn/3/library/asyncio.html) 基础.

    若没有 `Python 3.7+` 基础, 请移步 [`Python 教程`](https://www.runoob.com/python3/python3-tutorial.html)

    若没有 `asyncio` 基础, 请移步 [`asyncio 入门`](appendix/asyncio-intro.md)

    开发者不会负责 `Python` 基础教学.

## 安装

```bash
pip install graia-ariadne
# 使用 poetry(推荐的方式)
poetry add graia-ariadne
```

这同时会安装 `graia-ariadne` 和 `graia-broadcast` 这两个包的最新版本.

!!!info "提示"

    如果你想更新其中的一个:

    ``` bash
    # 更新 graia-ariadne
    pip install graia-ariadne --upgrade
    ## 使用 poetry
    poetry update graia-ariadne
    # 更新 graia-broadcast
    pip install graia-broadcast --upgrade
    ## 使用 poetry
    poetry update graia-broadcast
    ```

## 第一次对话

现在我们需要协定好 `mirai-api-http` 的配置, 以便于接下来的说明.

根据 `mirai-api-http` 的相关文档, 我们可以得出这么一个配置文件的方案:

```yaml
# file: "MCL/config/net.mamoe.mirai-api-http/setting.yml"
adapters:
  - http
  - ws
debug: false
enableVerify: true
verifyKey: ServiceVerifyKey # 你可以自己设定, 这里作为示范
singleMode: false
cacheSize: 4096 # 可选，缓存大小，默认4096. 缓存过小会导致引用回复与撤回消息失败
adapterSettings:
  ## 详情看 http adapter 使用说明 配置
  http:
    host: localhost
    port: 8080 # 端口
    cors: [*]

  ## 详情看 websocket adapter 使用说明 配置
  ws:
    host: localhost
    port: 8080 # 端口
    reservedSyncId: -1 # 确保为 -1, 否则 WebsocketAdapter(Experimental) 没法正常工作.
```

将以下代码保存到文件 `bot.py` 内, 确保该文件位于你的工作区内:

```python
import asyncio

from graia.broadcast import Broadcast

from graia.ariadne.adapter import DefaultAdapter
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend, MiraiSession

loop = asyncio.new_event_loop()

bcc = Broadcast(loop=loop)
app = Ariadne(
    broadcast=bcc,
    adapter=DefaultAdapter(
        bcc,
        MiraiSession(
            host="http://localhost:8080",  # 填入 HTTP API 服务运行的地址
            verify_key="ServiceVerifyKey",  # 填入 verifyKey
            account=123456789,  # 你的机器人的 qq 号
        ),
    ),
)


@bcc.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne, friend: Friend):
    await app.sendMessage(friend, MessageChain.create([Plain("Hello, World!")]))
    # 实际上 MessageChain.create(...) 有没有 "[]" 都没关系


loop.run_until_complete(app.lifecycle())
```

!!! info "技巧"

    将 `CombinedAdapter` 换为 `DebugAdapter` 可以输出所有接收到的事件, 但在生产环境下并不推荐.

!!! note "提示"

    如果你对 `v4 (graia-application-mirai)` 中的初始化方法念念不忘, 你也可以这样做 (并且这样签名更简单)

    !!!important "重要"

        但是这样你无法利用下一章中的部分配置特性.

    ```python
    session = MiraiSession(...) # 自行替换 MiraiSession 内容
    app = Ariadne.create(session=session)
    loop = app.loop
    bcc = app.broadcast
    ```
