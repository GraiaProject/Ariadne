# 函数异步化

`Ariadne` 在 `util.async_exec` 模块里提供了 `io_bound` 与 `cpu_bound` 两个函数,
可以用于方便的将普通函数异步化以防止阻塞.

## 用法

首先导入:

```py
from graia.ariadne.util.async_exec import io_bound, cpu_bound
```

然后对函数包装:

```py
@cpu_bound
def foo(n: int) -> int:
    ans = 0
    for i in range(1, n + 1):
        ans += i ** i
    return ans
```

这时, `foo` 的签名就从原来的 `(n: int) -> int` 变为了 `(n: int) -> Awaitable[int]`.

在其他地方, 使用 `await foo(50000)` 来异步地调用这个函数.

!!! error "警告"

    **这两个装饰器都不能用于动态创建的函数 (如闭包, lambda 表达式).**

`io_bound` 包装过的函数是在单独 **线程** 中运行的，

`cpu_bound` 包装过的函数是在单独 **进程** 中运行的，

!!! warning "限制"

    因为 `cpu_bound` 的参数是通过 `pickle` 传入的, 所以不要想着传递奇奇怪怪的对象作为参数 (文件, 窗口, 进程, 协程等).

## 进一步控制

要进一步控制, 可以从 `graia.ariadne.util.async_exec` 导入 `ParallelExecutor`.

通过提前执行 `ParallelExecutor(loop=app.loop, max_thread=max_t, max_proc=max_p)` 可以控制并行执行器的最大线程, 进程数.

`loop` 可以在之后通过 `bind_loop` 函数传入.

## 原理

因为被 `io_bound` `cpu_bound` 包装的函数在另一个进程中无法访问到其原有函数,

我们在 `ParallelExecutor` 的类变量 `func_mapping` 中存储了函数的 `__qualname__` 至原函数本身的映射.

这样执行时 `io_bound` `cpu_bound` 只传递 `__qualname__` 与 `__module__` 给实际的执行函数, 它会通过导入 `__module__` 完成另一个进程中的函数注册.
之后通过 `ParallelExecutor.func_mapping[func_qualname](*args, **kwargs)` 完成调用.
