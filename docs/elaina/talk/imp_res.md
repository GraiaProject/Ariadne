# importlib.resources 简要概述

在最近拿 Ariadne 写 `Github Bot` 的时候, 我碰到了需要引用外部 `gql` 文件(GraphQL 的描述文件)的需求,
在解决这个问题时, 我使用了 `importlib.resources` 这个标准库模块.

我将在这个 LightTalk 中简单介绍这个模块的使用方法.

这个模块用于在 Python Module / Package 中引用静态文件,
并允许 `poetry` 等打包工具将该静态文件放入包中并发布到 `pypi`.

!!! info "关于 `Saya` 模块的发布方式"
我在很多的, 像是 A60, Redlnn 等人的 Graia 应用中看到他们使用了 `modules`, `plugins` 这种类似 `Bukkit` 的目录模式.
事实上, 由于我并没有对关于 `Saya` 模块和使用到 `Saya` 的应用写文档指导,
这种情况反而是在我意料之中... 就算我强行推进我想象的理想架构, Python 现在也没有类似 lerna 这样的用于 monorepo 模式开发的包管理工具...
 那么我就先做个示范吧.

# 目录结构展示

```
stellaium
    └─order_1
        ├─commands
        ├─github
           ├─commands
           |    └─ repo.py
           └─resources
                └─ __init__.py
                └─ simple_repo_info.gql
```

我们将 `stellaium.order_1.github.resources` 作为我们的 `资源包`, 并在其他的地方引用.

这里以引用 `simple_repo_info.gql` 文件作为示范.

```python
import importlib.resources as pkg_resources
import stellaium.order_1.github.resources as resources

with pkg_resources.path(resources, "simple_repo_info.gql") as file:
    ... # file 在这里是个 pathlib.Path, 也就是说可以 read_text 和 read_bytes.
```

如果你的包管理工具配置正确(通常来讲不需要多做什么事, 除非你配置了 glob), 静态资源文件也会被打包.

这种方式减少了对于启动 Saya 应用时强加的运行目录要求.

!!! tip "请不要将数据库文件/配置文件/含有用户数据的文件作为静态资源."
