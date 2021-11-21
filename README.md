<div align="center">

# Ariadne

_another elegant framework for mirai and mirai-api-http v2_

> 接受当下, 面向未来.

</div>

<p align="center">

[![License](https://img.shields.io/github/license/GraiaProject/Ariadne)](https://github.com/GraiaProject/Ariadne/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/graia-ariadne)](https://pypi.org/project/graia-ariadne)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/graia-ariadne)](https://www.python.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?labelColor=ef8336)](https://pycqa.github.io/isort/)

</p>

---

[API 文档](https://graiaproject.github.io/Ariadne/) 部署状态:
[![PDoc Deploy](https://img.shields.io/github/deployments/GraiaProject/Ariadne/github-pages)](https://graiaproject.github.io/Ariadne/)

[入门文档](https://graia.readthedocs.io/zh_CN/latest/)部署状态：
[![Read The Docs Deploy](https://readthedocs.org/projects/graia/badge/?version=latest)](https://graia.readthedocs.io/zh_CN/latest/)

一个适用于 [`mirai-api-http v2`](https://github.com/project-mirai/mirai-api-http) 的 Python SDK.

**本项目适用于 mirai-api-http 2.0 以上版本**.

目前仍处于开发阶段, 内部接口可能会有较大的变化.

## 安装

`poetry add graia-ariadne`

或

`pip install graia-ariadne`

## 使用

```python
import asyncio

from graia.broadcast import Broadcast

from graia.ariadne.adapter import DefaultAdapter
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend, MiraiSession

loop = asyncio.new_event_loop()

app = Ariadne(MiraiSession(host="http://localhost:8080", verify_key="ServiceVerifyKey", account=123456789)))


@app.broadcast.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne, friend: Friend):
    await app.sendMessage(friend, MessageChain.create([Plain("Hello, World!")]))


loop.run_until_complete(app.lifecycle())
```

更多信息请看 [文档](https://graia.readthedocs.io/zh_CN/latest/).

## 讨论

QQ 交流群: [邀请链接](https://jq.qq.com/?_wv=1027&k=VXp6plBD)

## 文档

[API 文档](https://graiaproject.github.io/Ariadne/) [文档](https://graia.readthedocs.io/zh_CN/latest/)

[鸣谢](https://graia.readthedocs.io/zh_CN/latest/appendix/credits)

## 协议

本项目以[`GNU AGPLv3`](https://choosealicense.com/licenses/agpl-3.0/) 作为开源协议, 这意味着你需要遵守相应的规则.
