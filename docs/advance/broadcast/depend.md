# Depend - 依赖注入

有时, 前面介绍的基础消息链处理器与 `Twilight` 消息链处理器, 都不能满足我们的需求. 例如, 对某些数据 (好友号, 群号, 权限等) 的主动判断.

此时, `Depend` 即可助你一臂之力. 我们可利用其构造一个 `Decorator`.

!!! info "你可以从 `graia.broadcast.builtin.decorators` 导入 `Depend`."

!!! warning "这里所说的 `Decorator` 是 `Graia Broadcast` 的一部分, 而非 Python 的 `@decorator` 语法糖. "

## 基础: 用于验证的依赖

首先, 我们需要实现一个异步函数. 它可以接收 [与事件处理函数相同的参数](../../../basic/params/). 如果我们想对群号进行检查, 可以这样写：

```python
async def check_group(group: Group):
    if group.id != 12345678:
        raise ExecutionStop
```

这里, 触发的 `ExecutionStop` 异常, 会结束 Ariadne 对消息的处理, 也就是说, 除了群号为 `12345678` 以外的群里有消息时, 机器人就不会响应了.

我们用 `Depend(check_group)` 创建一个 `Decorator` , 并把它传入 `broadcast.receiver` 中:

```python
@broadcast.receiver(GroupMessage, decorators=[Depend(check_group)])
async def foo(...): ...
```

???+ "什么是 `依赖注入`?"

    `依赖注入` 这个词听起来挺高大上, 但实际上它的设计思想只有一个: 代码复用.

    上面你用 `Depend` 注入的函数, 基本等价于以下表示:

    === "不用 Depend"

        ```python
        @broadcast.receiver(GroupMessage)
        async def foo(..., group: Group):
            if group.id != 12345678:
                raise ExecutionStop
            ... # 跳过其他代码
        ```

    === "使用 Depend"

        ```python
        @broadcast.receiver(GroupMessage, decorators=[Depend(check_group)])
        async def foo(...): ...
        ```


运行机器人进行测试, 此时机器人只会响应群号为 12345678 的群里的消息.

!!! note "提示"

    你也可以创建一个包装器函数:

    ```py
    def require_group(*group_id: int):
        async def wrapper(group: Group):
            if group.id not in group_id:
                raise ExecutionStop
        return wrapper

    @broadcast.receiver(GroupMessage, decorators=[Depend(require_group(12345678, 87654321))])
    async def foo(...): ...
    ```

`Decorator` 也可以配合前面提到的基础消息链处理器, 还有 `Twilight` 一起使用:

```python
@broadcast.receiver(
    GroupMessage,
    dispatchers=[Twilight(Sparkle([UnionMatch("get_data", "data")]))],
    decorators=[Depend(check_group)],
)
async def get_data(...): ...
```

## 下一步: 代码复用

`Depend` 可以返回值, 以便你在函数中直接使用.

比如, 假设你想写一个自动提取消息中图片, 并自动下载其 `bytes` 的 `Depend`:

!!! info "这里我们将使用 `Python` 的 `@decorator` 直接包装这个内部函数."

```python
@Depend
async def get_img_bytes(chain: MessageChain) -> List[bytes]:
    result: List[bytes] = []
    for element in chain:
        if isinstance(element, Image):
            result.append(await element.get_bytes())
    return result

# example
@broadcast.receiver(GroupMessage)
async def save_images(..., img_bytes: List[bytes] = get_img_bytes):
    for img_bytes in img_bytes:
        ... # do sth
```

就是这样! 你可以且应该通过在函数定义的 `默认值` 位置放置 `Decorator` 来创建所谓的 “有头装饰器” ,

`Depend` 包装函数所返回的 **所有** 值 (包括 `None`) 都会被传递回去. 同样, 引发的 `ExecutionStop` 会招致执行的停止.

最后顺口一提, 有头和无头装饰器并不冲突.

!!! graiax "社区文档相关章节: [链接](https://graiax.cn/guide/depend.html)"
