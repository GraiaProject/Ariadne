# asyncio 入门

`asyncio` 在 Python 3.4 即成为标准库, 我们在这里使用 3.9 版本.

## 导入模块

非常简单的操作, 使用 `import` 即可.

```python
import asyncio
```

## 声明异步函数 / 方法

同样非常简单, 在 `3.5` 版本中就有 `async` 和 `await` 两个关键字.  
`await` 关键字用于在一个异步执行内调用其他的异步函数/方法并获取其返回值.

```python
async def func1(arg1, arg2):
    return arg1 + arg2
async def func2():
    func1_return = await func1(1, 2)
    return func1_return
```

用在类的声明里也一样, 但不要用来声明魔法方法, 也不要用于 `property`.

```python
class Example:
    async def method1(self, arg1):
        return self.var1 + arg1 + 1

    async def method2(self):
        return await self.method1(2)
```

## 创建事件循环 (Event Loop) 对象

事件循环用来在 `async` 代码块外部运行异步相关的东西. 与同步相对的就是异步, 你这样理解就好.

简单调用 `asyncio.new_event_loop()` 即可获取事件循环对象.

```python
loop = asyncio.new_event_loop()
```

!!! note "提示"

    可以使用 `asyncio.get_running_loop()` 获取当前 **正在运行的** 事件循环.

!!!important "重要"

    3.10 以后使用 `asyncio.get_event_loop()` 创建事件循环被弃用.

## 运行异步函数 / 方法

使用 `loop.run_until_complete` 或者 `asyncio.run()`.

```python
loop.run_until_complete(async_callable(arg1, arg2))
# 效果同
asyncio.run(async_callable(arg1, arg2))
```

## 将异步执行丢到后台

本方法经常被用于创建后台任务, 但请注意, 原则上请不要滥用.

使用 `loop.create_task` 方法即可, 你可以通过 `await` 这个方法的返回值堵塞当前运行.

!!! note "提示"

    也可以使用 `asyncio.create_task()`.

```python
async def main():
    task = loop.create_task(background_exec(arg1, arg2))
    # do sth
    await task # 等待这个任务完成
```

就这样, 只要你知道 "在另外一个异步函数内, 只能用 `await` 执行其他异步函数",

然后其他的像 `async with`, `__await__` 之类的自己去学吧,

不用黑魔法(我完全不能理解为什么有人称 `asyncio` 为黑魔法, 这玩意基础的不行),

凭这些你就可以去愉快的用 Graia 相关的东西了.
