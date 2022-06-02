# 项目概览

!!! error "交涉提示"

    若你在使用的过程中遇到了问题, 请运用[提问的智慧](https://github.com/ryanhanwu/How-To-Ask-Questions-The-Smart-Way/blob/main/README-zh_CN.md).

    在与你交流的过程中, 我们有很大可能使用 [术语](./appendix/terms) 以提高交流效率.

    我们会持续追踪并修复已存在的[问题](https://github.com/GraiaProject/Ariadne/issues)并不断改进, 但是...

    我们没有任何义务回答你的问题, 这仅仅是我们的自愿行为.

## 简介

[`Ariadne`](https://github.com/GraiaProject/Ariadne) 是 [`BlueGlassBlock`](https://github.com/BlueGlassBlock) 基于
[`Graia Project`](https://github.com/GraiaProject/) 系列依赖库而编写的
**简明, 优雅** 的 聊天软件自动化框架. 其丰富而简洁的接口相信可以使开发者能更好的完成业务逻辑.

**如果认为本项目有帮助, 欢迎点一个 `Star`.**

> 接受当下, 面向未来.

## 特色

### 易于伸缩

从单文件的最小示例, 到模块化的大型机器人, `Ariadne` 都可以满足你的需求.

=== "单文件"

    ```py
    from graia.ariadne.entry import Ariadne, Friend, MessageChain, config


    app = Ariadne(
        config(
            verify_key="ServiceVerifyKey",
            account=123456789,
        )
    )


    @app.broadcast.receiver("FriendMessage")
    async def friend_message_listener(app: Ariadne, friend: Friend):
        await app.send_message(friend, "Hello, World!")


    Ariadne.launch_blocking()
    ```

=== "模块化"

    ```markdown
    - main.py
    - modules
        - function_1
        - function_2
            - __init__.py
            - manager.py
            - ...
        - ...
    ```

### 轻松编写

基于类型标注与参数分派的开发, 使开发者可以轻松编写逻辑.

```py
@broadcast.receiver(GroupMessage)
async def handler(
    app: Ariadne,
    src: Source,
    msg: MessageChain,
    group: Group,
    member: Member,
    ...
): ...
```

### 异步开发

基于异步的并发设计, 使得 `Ariadne` 可以轻松对事件并行处理.

```py
@broadcast.receiver(GroupMessage)
async def reply1(app: Ariadne, msg: MessageChain, group: Group):
    await app.send_message(group, "你好") # 回复 你好
```

### 便于拓展

`Dispatcher` `Decorator` `Interrupt` `Depend` 等 `Broadcast Control` 特性使得

权限匹配, 冷却控制, 异常处理, 资源获取等操作可以被轻松封装.

`Saya` `Scheduler` 封装了模块化与定时任务操作, 大大提高了 `Ariadne` 的可用性.

## 加入我们

我们非常希望有志之士能帮助完善这个项目, 若你有意参与,
可前往 [GitHub 组织](https://github.com/GraiaProject/Ariadne) 了解我们的项目体系.

你可以通过以下几种方式参与进来:

-   [提交 issue](https://github.com/GraiaProject/Ariadne/issues/new/choose) _包括但不限于 bug 汇报, 新功能提案, 文档改进等._
-   发起 [Pull Requests](https://github.com/GraiaProject/Ariadne/pulls) _直接将 想法 / 修复 合并到代码库中._

同时, 欢迎加入我们的 [QQ 群](https://jq.qq.com/?_wv=1027&k=VXp6plBD) 与开发者进行直接交流.

> QQ 群不定时清除不活跃成员, 可重新申请入群.
