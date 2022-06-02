# 快速开始

## 前言

这里我们假设你已经参照 [ `mirai` ](https://github.com/mamoe/mirai) 和 [ `mirai-api-http` ](https://github.com/mamoe/mirai-api-http)
的 README,

启动了你的 `mirai-console` , 同时也安装了最新版本的 `mirai-api-http` 插件.

!!! error "注意"

    本 快速开始 文档假设你已有 [`Python 3`](https://docs.python.org/zh-cn/3/) 与 [`asyncio`](https://docs.python.org/zh-cn/3/library/asyncio.html) 基础.

    若没有 `Python 3` 基础, 请移步 [`Python 教程`](https://www.runoob.com/python3/python3-tutorial.html) [`Python 官方教程`](https://docs.python.org/zh-cn/3/tutorial/index.html)

    若没有 `asyncio` 基础, 请移步 [`asyncio 入门`](appendix/asyncio-intro.md)

    开发者不会负责 `Python` 基础教学.

    如果你还不会使用 `mirai-console`，请移步:

    - [`Mirai API HTTP 安装`](appendix/mah-install.md)
    - [社区文档: `Mirai` 的配置](https://graiax.cn/before/install_mirai.html)

    如果你使用时开发库出现了错误, 应先检查是否是 `Graia Framework` 的错误,
    确认之后, 请在我们的 [GitHub Issues](https://github.com/GraiaProject/Ariadne/issues) 处汇报你的错误,
    我们会尽快处理问题

!!! warning "提示"

    本框架支持的版本:

    <a href="https://pypi.org/project/graia-ariadne"><img alt="Python Version" src="https://img.shields.io/pypi/pyversions/graia-ariadne" /></a>
    <a href="https://pypi.org/project/graia-ariadne"><img alt="Python Implementation" src="https://img.shields.io/pypi/implementation/graia-ariadne" /></a>

    如果你的 `Python` 版本不满足, 请下载对应版本的 `Python`.

    !!! quote "[`华为云 Python 镜像`](https://mirrors.huaweicloud.com/python/) [`清华 PyPI 源帮助`](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/)"

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
## 配置文件中的值，全为默认值

## 启用的 adapter, 内置有 http, ws, reverse-ws, webhook
adapters:
  - http
  - ws

## 是否开启认证流程, 若为 true 则建立连接时需要验证 verifyKey
enableVerify: true
verifyKey: ServiceVerifyKey

## 开启一些调试信息
debug: false

## 是否开启单 session 模式, 不建议开启
singleMode: false

## 历史消息的缓存大小
## 同时，也是 http adapter 的消息队列容量
cacheSize: 4096

## adapter 的单独配置，键名与 adapters 项配置相同
## 注意: 如果 mirai 读取配置时出错可以尝试删除并重新写入
adapterSettings:
  ## HTTP 服务的主机, 端口和跨域设置
  http:
    host: localhost
    port: 8080
    cors: ["*"]

  ## Websocket 服务的主机, 端口和事件同步ID设置
  ws:
    host: localhost
    port: 8080
    reservedSyncId: -1

```

将以下代码保存到文件 `bot.py` 内, 确保该文件位于你的工作区内:

```python
from graia.ariadne.app import Ariadne
from graia.ariadne.entry import config
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend

app = Ariadne(
    config(
        verify_key="ServiceVerifyKey",  # 填入 VerifyKey
        account=123456789,  # 你的机器人的 qq 号
    ),
)

@app.broadcast.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne, friend: Friend):
    await app.send_message(friend, MessageChain([Plain("Hello, World!")]))
    # 实际上 MessageChain(...) 有没有 "[]" 都没关系

app.launch_blocking()

```

!!! graiax "社区文档相关章节: [链接](https://graiax.cn/guide/hello_ero.html)"

    你知道吗? `Graia Framework` 有一个活跃的社区文档: [`GraiaX`](https://graiax.cn/).

    那里的教程会更加<ruby>通俗易懂<rt><span class="curtain">但是在不适宜场合阅读可能导致社死</span></rt></ruby>, 你随时可以回来这里获得更详细的解释.
