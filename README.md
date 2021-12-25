<div align="center">

# Ariadne

_Another elegant framework for mirai and mirai-api-http v2._

> 接受当下, 面向未来.

</div>

<p align="center">
  <a href="https://github.com/GraiaProject/Ariadne/blob/master/LICENSE"><img alt="License" src="https://img.shields.io/github/license/GraiaProject/Ariadne"></a>
  <a href="https://pypi.org/project/graia-ariadne"><img alt="PyPI" src="https://img.shields.io/pypi/v/graia-ariadne" /></a>
  <a href="https://pypi.org/project/graia-ariadne"><img alt="Python Version" src="https://img.shields.io/pypi/pyversions/graia-ariadne" /></a>
  <a href="https://pypi.org/project/graia-ariadne"><img alt="Python Implementation" src="https://img.shields.io/pypi/implementation/graia-ariadne" /></a>
  <a href="https://graia.readthedocs.io/zh_CN/latest"><img alt="docs" src="https://img.shields.io/badge/文档_@_readthedocs-click_here-black" /></a>
  <a href="https://graiaproject.github.io/Ariadne/"><img alt="API docs" src="https://img.shields.io/badge/API_文档_@_GitHub_Pages-click_here-black"></a>
  <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="black" /></a>
  <a href="https://pycqa.github.io/isort/"><img src="https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336" alt="isort"/></a>
</p>

**本项目适用于 mirai-api-http 2.0 以上版本**.

Ariadne 是 `Graia Project` 继承了 [`Application`](https://github.com/GraiaProject/Applicaiton) 并进行了许多改进后产生的作品,
相信它可以给你带来良好的 `Python QQ Bot` 开发体验.

**注意, 本框架需要 [`mirai-api-http v2`](https://github.com/project-mirai/mirai-api-http).**

## 安装

`poetry add graia-ariadne`

或

`pip install graia-ariadne`

> 我们强烈建议使用 [`poetry`](https://python-poetry.org) 进行管理

## 开始使用

```python
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.model import Friend, MiraiSession

app = Ariadne(MiraiSession(host="http://localhost:8080", verify_key="ServiceVerifyKey", account=123456789))


@app.broadcast.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne, friend: Friend):
    await app.sendMessage(friend, MessageChain.create([Plain("Hello, World!")]))


app.launch_blocking()
```

更多信息请看 [文档](https://graia.readthedocs.io/zh_CN/latest/).

## 讨论

QQ 交流群: [邀请链接](https://jq.qq.com/?_wv=1027&k=VXp6plBD)

## 文档

[API 文档](https://graiaproject.github.io/Ariadne/)
[![PDoc Deploy](https://img.shields.io/github/deployments/GraiaProject/Ariadne/github-pages)](https://graiaproject.github.io/Ariadne/)

[文档](https://graia.readthedocs.io/zh_CN/latest/)
[![Read The Docs Deploy](https://readthedocs.org/projects/graia/badge/?version=latest)](https://graia.readthedocs.io/zh_CN/latest/)

[鸣谢](https://graia.readthedocs.io/zh_CN/latest/appendix/credits)

**如果认为本项目有帮助, 欢迎点一个 `Star`.**

## 协议

本项目以[`GNU AGPLv3`](https://choosealicense.com/licenses/agpl-3.0/) 作为开源协议, 这意味着你需要遵守相应的规则.

## 开发构建

[开发分支文档](https://graia-dev.rtfd.io/)

[开发分支](https://github.com/GraiaProject/Ariadne/tree/dev)

[开发版构建 PyPI](https://pypi.org/project/graia-ariadne-dev) [![Dev PyPI Version](https://img.shields.io/pypi/v/graia-ariadne-dev)](https://pypi.org/project/graia-ariadne-dev)

[开始开发](./)