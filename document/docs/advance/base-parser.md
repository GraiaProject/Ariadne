# 基础消息链处理器

!!! info "提示"

    这里介绍的所有处理器都是 `Broadcast Decorator`.

    想知道更多关于 `Decorator` 的事可以点击 [这里](https://autumn-psi.vercel.app/docs/broadcast/basic/decorator).

本部分代码在 [`base.py`](https://github.com/GraiaProject/Ariadne/blob/master/src/graia/ariadne/message/parser/base.py)

## DetectPrefix

顾名思义, 检测前缀.

### 实例化

传入前缀 **字符串** 即可.

### 使用

作为 `Decorator`, 你应该放到 `broadcast.receiver` / `ListenerSchema` 的 `decorator` 参数列表里.

或者也可以这样:

```py
async def foo_func(chain: MessageChain = DetectPrefix(".test")):
    ...
```

这会自动去掉前缀. 但是不会改动 `Quote` 与 `Source` 等元数据元素.

无论如何, 前缀不匹配时它都会通过引发 `ExecutionStop` 停止执行.

## DetectSuffix

顾名思义, 检测后缀.

### 实例化

传入后缀 **字符串** 即可.

### 使用

作为 `Decorator`, 你应该放到 `broadcast.receiver` / `ListenerSchema` 的 `decorator` 参数列表里.

或者也可以这样:

```py
async def foo_func(chain: MessageChain = DetectSuffix("suffix")):
    ...
```

这会自动去掉后缀. 但是不会改动 `Quote` 与 `Source` 等元数据元素.

无论如何, 前缀不匹配时它都会通过引发 `ExecutionStop` 停止执行.
