# 开始使用

## 简介

> Saya 的名称取自作品 魔女之旅 中的角色 "沙耶(Saya)", 愿所有人的心中都有一位活泼可爱的炭之魔女.

Saya 的架构分为以下几个部分:

-   `Saya Controller` (控制器): 负责控制各个模块, 分配 `Channel`, 管理模块启停, `Behaviour` 的注册和调用.
-   `Module Channel` (模块容器): 负责对模块服务, 收集模块的各式信息, 像 模块的名称, 作者, 长段的描述 之类,
    并负责包装模块的内容为 `Cube`, 用以 `Behaviour` 对底层接口的操作.
-   `Cube` (内容容器): 对模块提供的内容附加一个由 `Schema` 实例化来的 `metadata`, 即 "元信息", 用于给 `Behaviour` 进行处理.
-   `Schema` (元信息模板): 用于给模块提供的内容附加不同类型的元信息, 给 `Behaviour` `isinstance` 处理用.
-   `Behaviour` (行为): 根据 `Cube` 及其元信息, 对底层接口(例如 `Broadcast`, `Scheduler` 等)进行操作.
    包括 `allocate` 与 `uninstall` 两个操作.

`Saya` 已经内置了对 `Broadcast Control` 的最基本的支持(即监听器 `Listener`), 下面我们就试下 `saya-style` 的 `Broadcast Control` 的使用.

首先, 我们需要先部署环境, 执行指令:

```bash
pip install graia-saya
```

或者使用 `poetry`:

```bash
poetry add graia-saya
```

目前, 所有的 API 都属于不稳定状态, 虽然基本的架构是不会变化, 但有些 API 可能在 `Saya@0.1.0` 发布前进行剧烈的变动,
所以请随时关注我们的更新状态!

安装后, 在编辑器内打开工作区, 创建如下的目录结构:

!!! note

    这里我们建立的是一个 **示例性** 目录结构, 即最小实例.

    理论上你的模块只需要符合 Python 的导入规则,
    就能引入模块到实例中.

```bash
saya-example
│  main.py
│  pyproject.toml
│
└─ modules
    │  __init__.py
    │  module_as_file.py # 作为文件的合法模块可以被调用.
    │
    └─ module_as_dir # 作为文件夹的合法模块可以被调用(仅调用 __init__.py 下的内容).
            __init__.py
```

`Saya` 需要一个入口(`entry`), 用于创建 `Controller`, 并让 `Controller` 分配 `Channel` 给这之后被 `Saya.require` 方法引入的模块.

`main.py` 将作为入口文件, 被 Python 解释器首先执行.

## 入口文件的编写

首先, 我们需要引入 `Saya`, `Broadcast`, 还有其内部集成的对 `Broadcast` 的支持:

```py
from graia.saya import Saya
from graia.broadcast import Broadcast
from graia.saya.builtins.broadcast import BroadcastBehaviour
```

分别创建 `Broadcast`, `Saya` 的实例:

```py
import asyncio
loop = asyncio.get_event_loop()
broadcast = Broadcast(loop=loop)
saya = Saya(broadcast)
```

!!! info "提示"

    你可以利用 `Ariadne.create` 方法, 方便的创建 `Saya` 实例.

    ```py
    from graia.saya import Saya
    app = Ariadne(...)
    saya = Ariadne.create(Saya)
    ```

    只要记得在启动 `Ariadne` 前这么做就好.

创建 `BroadcastBehaviour` 的实例, 并将其注册到现有的 `Saya` 实例中:

```py
saya.install_behaviours(BroadcastBehaviour(broadcast))
```

!!! note "提示"

    你也可以用 `Ariadne.create` 创建 `BroadcastBehaviour`.

为了导入各个模块, `Saya Controller` 需要先进入上下文:

```py
with saya.module_context():
    ...
```

引入各个模块, 这里的模块目前都需要手动引入, 后期可能会加入配置系统:

```py
with saya.module_context():
    saya.require("modules.module_as_file")
    saya.require("modules.module_as_dir")
```

!!! note "提示"

    要配合 Ariadne 使用, 可以直接这样做:

    ```py
    app = Ariadne(...)

    app.launch_blocking()
    ```

最终的结果:

```py title="main.py"
import asyncio
from graia.saya import Saya
from graia.broadcast import Broadcast
from graia.saya.builtins.broadcast import BroadcastBehaviour
loop = asyncio.get_event_loop()
broadcast = Broadcast(loop=loop)
saya = Saya(broadcast)
saya.install_behaviours(BroadcastBehaviour(broadcast))
with saya.module_context():
    saya.require("modules.module_as_file")
    saya.require("modules.module_as_dir")
try: # 仅用于调试
    loop.run_forever()
except KeyboardInterrupt:
    exit()
```

!!! note "提示"

    实际上 `with saya.module_context():` 是给 `require` 导入的模块提供 `Saya` 实例的上下文,
    从而可以使用 `Saya.current()` 获取当前 `Saya` 实例.

就这样, 一个入口文件就这样完成了, 现在主要是插件部分.

## 第一次运行

来到 `module_as_file.py`:

```py
from graia.saya import Saya, Channel
saya = Saya.current()
channel = Channel.current()
```

两个 `current` 方法的调用, 访问了 `Saya` 实例和当前上下文分配的 `Channel`.

接下来, 导入 `ListenerSchema`:

```py
from graia.saya.builtins.broadcast.schema import ListenerSchema
```

`ListenerSchema` 作为 `Schema`, 标识相对应的模块内容为一 `Listener`,
并在模块被导入后经由 `Behaviour` 进行操作.

使用 `Channel.use` 方法, 向 `Channel` 提供内容:

```py
@channel.use(ListenerSchema(
    listening_events=[...] # 填入你需要监听的事件
))
async def module_listener():
    print("事件被触发!!!!")
```

然后, 引入结束, `module_as_file.py` 文件内容如下, 这里我们监听 `SayaModuleInstalled` 事件, 作为 `Lifecycle API` 的简单示例:

```py title="Result of module_as_file.py"
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.saya.event import SayaModuleInstalled
saya = Saya.current()
channel = Channel.current()

@channel.use(ListenerSchema(
    listening_events=[SayaModuleInstalled]
))
async def module_listener(event: SayaModuleInstalled):
    print(f"{event.module} :: 模块加载成功!!!")

```

我们对 `modules/module_as_dir/__init__.py` 也如法炮制, copy 上方的代码, 进入虚拟环境, 然后运行 `main.py`.

!!! error "警告"

    请不要直接运行 `Saya module`, 而需要通过主文件运行, 否则会因为没有分配 `Channel` 产生 `LookupError` 异常.

```
root@localhost: # python main.py
2021-02-16 01:19:56.632 | DEBUG | graia.saya:require:58 - require modules.module_as_file
2021-02-16 01:19:56.639 | DEBUG | graia.saya:require:58 - require modules.module_as_dir
modules.module_as_file :: 模块加载成功!!!
modules.module_as_file :: 模块加载成功!!!
modules.module_as_dir :: 模块加载成功!!!
modules.module_as_dir :: 模块加载成功!!!
```

恭喜你, 完成了第一个 `Saya Application`, 我们可以前往下一章了.

!!! graiax "社区文档相关章节: [链接](https://graiax.cn/guide/saya.html)"
