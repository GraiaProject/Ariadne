# 使用 Channel

推荐在模块开头使用 `channel = Channel.current()` 后, 使用以下方法:

-   `channel.name(str)`: 定义插件名字.
-   `channel.author(str)`: 定义插件的作者 (你自己).
-   `channel.description(str)`: 定义插件描述 (通常是使用方法).

!!! info "提示"

    这些可以通过 `Channel` 的 `_name`, `_author`, `_description` 属性获取.

## channel.use

这是 `Channel` 的核心方法. 也是 `Saya module` 与其他部分交互的首选途径.

### 用法

你需要一个 `Schema` 对象, 之后

```py
@channel.use(SchemaObject)
async def fetch(...):
    ...
```

即可. 与其他函数定义方式相同.

有以下几个 `Schema`.

-   `ListenerSchema`: 需要 `BroadcastBehaviour`, 相当于使用 `broadcast.receiver`.
-   `SchedulerSchema`: 需要 `GraiaSchedulerBehaviour`, 相当于使用 `scheduler.schedule`.

!!! note "提示"

    你可以创建主文件 ( `main.py` ) 的 `Saya Channel` !

    只需要调用 `Saya.create_main_channel()` 即可.

## 不只是 Schema 调用

还记得我们在刚刚的 [快速开始](./start) 中所用到的这部分吗?

```py
with saya.module_context():
    saya.require("modules.module_as_file")
    saya.require("modules.module_as_dir")
```

`Saya.require` 是有返回值的, 正常情况下返回的是当前的 `Channel` 对象, 与 `Channel.current()` 是一个东西.

但是, 使用 `channel.export` 可以返回不一样的东西给 `require` ...

```py title="module_as_file.py 的一部分" hl_lines="3"
channel = Channel.current()

@channel.export
def exported_func(...):
    ...
```

```py title="main.py 的一部分"
func = saya.require("modules.module_as_file")
```

现在, `main.py` 下的 `func` 与 `module_as_file.py` 中的 `exported_func` 是一个函数.

## Channel 的其他用法

`Channel` 有如下用法:

-   `channel.name(str)`: 定义插件名字.

-   `channel.author(str)`: 定义插件的作者 (你自己).

-   `channel.description(str)`: 定义插件描述 (通常是使用方法).

-   `channel.export(obj)`: 导出一个对象, 可作为装饰器使用.

-   `channel.use(Schema)`: 使用一个 `Schema` 对象.

-   `channel._py_module`: 访问自身的 `Python` 模块, 注意导入完成后才可用.

-   `channel.meta`: 透明的元数据字典, `description` `author` `name` 方法都是对其的透明代理访问.
