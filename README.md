<div align="center">

# Ariadne

_Another elegant framework for mirai and mirai-api-http v2._

> 接受当下, 面向未来.

<a href="https://pypi.org/project/graia-ariadne"><img alt="PyPI" src="https://img.shields.io/pypi/v/graia-ariadne" /></a></td>
<a href="https://pypi.org/project/graia-ariadne"><img alt="PyPI Pre Release" src="https://img.shields.io/github/v/tag/GraiaProject/Ariadne?include_prereleases&label=latest&color=orange"></td>
<a href="https://pypi.org/project/graia-ariadne"><img alt="Python Version" src="https://img.shields.io/pypi/pyversions/graia-ariadne" /></a>
<a href="https://pypi.org/project/graia-ariadne"><img alt="Python Implementation" src="https://img.shields.io/pypi/implementation/graia-ariadne" /></a>

<a href="https://graia.readthedocs.io/projects/ariadne/"><img alt="docs" src="https://img.shields.io/badge/文档-here-blue" /></a>
<a href="https://graia.readthedocs.io/projects/ariadne/refs/graia/ariadne/"><img alt="API docs" src="https://img.shields.io/badge/API_文档-here-purple"></a>
<a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-black.svg" alt="black" /></a>
<a href="https://pycqa.github.io/isort/"><img src="https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat" alt="isort"/></a>
<a href="https://github.com/GraiaProject/Ariadne/blob/master/LICENSE"><img alt="License" src="https://img.shields.io/github/license/GraiaProject/Ariadne"></a>

</div>

**本项目适用于 mirai-api-http 2.0 以上版本**.

Ariadne 是 `Graia Project` 继承了 [`Application`](https://github.com/GraiaProject/Application) 并进行了许多改进后产生的作品,
相信它可以给你带来良好的 `Python QQ Bot` 开发体验.

**注意, 本框架需要 [`mirai-api-http v2`](https://github.com/project-mirai/mirai-api-http).**

## 安装

`poetry add graia-ariadne`

或

`pip install graia-ariadne`

> 我们强烈建议使用 [`poetry`](https://python-poetry.org) 进行包管理

## 开始使用

```python
from graia.ariadne.app import Ariadne
from graia.ariadne.connection.config import config
from graia.ariadne.model import Friend

app = Ariadne(config(verify_key="ServiceVerifyKey", account=123456789))


@app.broadcast.receiver("FriendMessage")
async def friend_message_listener(app: Ariadne, friend: Friend):
    await app.send_message(friend, "Hello, World!")


Ariadne.launch_blocking()
```

更多信息请看
[![快速开始](https://img.shields.io/badge/文档-快速开始-blue)](https://graia.readthedocs.io/projects/ariadne/quickstart/)

## 讨论

QQ 交流群: [邀请链接](https://jq.qq.com/?_wv=1027&k=VXp6plBD)

> QQ 群不定时清除不活跃成员, 请自行重新申请入群.

## 文档

[![API 文档](https://img.shields.io/badge/API_文档-here-purple)](https://graia.readthedocs.io/projects/ariadne/refs/graia/ariadne/)
[![官方文档](https://img.shields.io/badge/官方文档-here-blue)](https://graia.readthedocs.io/projects/ariadne/)
[![社区文档](https://img.shields.io/badge/社区文档-here-pink)](https://graiax.cn)
[![鸣谢](https://img.shields.io/badge/鸣谢-here-lightgreen)](https://graia.readthedocs.io/projects/ariadne/appendix/credits)

**如果认为本项目有帮助, 欢迎点一个 `Star`.**

## 协议

本项目以 [`GNU AGPL-3.0`](https://choosealicense.com/licenses/agpl-3.0/) 作为开源协议, 这意味着你需要遵守相应的规则.

## 持续集成 (CI) 状态

[![Documentation Status](https://readthedocs.org/projects/graia-ariadne/badge/?version=latest)](https://graia.readthedocs.io/projects/ariadne/)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/GraiaProject/Ariadne/master.svg)](https://results.pre-commit.ci/latest/github/GraiaProject/Ariadne/master)

[![文档构建](https://github.com/GraiaProject/Ariadne/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/GraiaProject/Ariadne/actions/workflows/deploy-docs.yml)
[![发布](https://github.com/GraiaProject/Ariadne/actions/workflows/release.yml/badge.svg)](https://github.com/GraiaProject/Ariadne/actions/workflows/release.yml)

## 参与开发

[贡献指南](./CONTRIBUTING.md)
