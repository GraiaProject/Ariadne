# 派生修饰 - Derive

如果你看到这里, 相信你大概通过 [基础消息链处理器](./../../basic/base-parser.md) 接触过 `Derive` 了.

它利用了 [`typing.Annotated`][typing.Annotated] 的特性, 为 `BroadcastControl` 提供了 `Decorator` 外的另一种参数修饰方式.

这个特性已被默认在 `BroadcastControl` 中启用.

## 使用

在声明参数时，使用这样的语法：

```py
arg: Annotated[OriginType, Derive1, Derive2, ...]
```

`Broadcast` 会获取 `OriginType` 作为初始值，之后 **逐个** 对剩下的 Derive **串行调用**，
如果没有失败，就返回最后的修饰值.

例如：

```py
chain: Annotated[MessageChain, MentionMe(name=False), StartsWith(".command")]
```

就会将 `MessageChain([At(123), ".command arg"])` 转换为 `MessageChain(["arg"])` 传回来.

!!! tip "跨版本兼容性"

    Python 3.8 用户请 `#!py from typing_extensions import Annotated`

## 自定义 Derive

`Derive` 应该是一个可调用对象, 签名为 `(T_Value, DispatcherInterface) -> T_Value`.

调用过程中引发的 `ExecutionStop` 异常会导致整个执行过程的终止, 就和 Decorator 一样.

例如:

```py
async def derive_chain(chain: MessageChain, interface: DispatcherInterface) -> MessageChain: # 注意 async
    ...

async def parse(chain: Annotated[MessageChain, derive_chain]):
    ...
```

你会注意到 `Derive` 的局限在于它不应用于改变返回值的类型, 比如从 MessageChain 变为 dict 之类的.

因此, 它是一个和 `Decorator` 同级的特性.
