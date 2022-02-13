# Depend - 依赖注入

有时, 前面介绍的基础消息链处理器与 `Twilight` 消息链处理器, 都不能满足我们的需求. 例如, 对某些数据 (好友号, 群号, 权限等) 的主动判断.

此时, `Depend` 即可助你一臂之力. 我们可利用其构造构造一个 `Headless Decorator`.

!!! info "你可以从 `graia.broadcast.builtin.decorators` 导入 `Depend`."

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

!!! graiax "社区文档相关章节: [链接](https://graiax.cn/make_ero_bot/tutorials/9_not_everyone_have_st.html)"