# Ariadne 总览

## 关于使用 "模型" 的提示

`Group` `Friend` `Member` `Stranger` 四个类型支持 `__int__` 协议获取其 `id` 属性.

也就是说, `int(group)` 等价于 `group.id` .

`Group` `Friend` `Member` 上还有 `get_info` `modify_info` `get_profile` `modify_admin` `get_config` `modify_config` `send_message` 等方便方法.

!!! tip "Member.send_temp_message 名字的不同是刻意为之的, 因为贸然使用临时消息非常容易导致风控. 谨慎使用."

`MemberPerm` 支持富比较操作, 也就是说你可以通过 `Member.permission >= MemberPerm.Administrator` 判断成员是否有管理权限.

!!! error "你 **不应该也不被允许** 自行实例化 `Group` `Friend` `Member` `Stranger` 类型."

## 某些事件的额外方法

[`RequestEvent`](https://github.com/GraiaProject/Ariadne/blob/master/src/graia/ariadne/event/mirai.py#L773)
带有一些额外方法, 如 `accept` `reject` `ignore` 等, 直接在其上使用 `await` 即可.

## 生命周期管理

`launch_blocking()` 用于启动 `Ariadne` 实例, `stop()` 用于停止 `Ariadne` 实例.

## 交互方法

`Ariadne` 与 QQ 进行交互的方法遵循以下原则:

- 使用 `snake_case` 小写 + 下划线的函数名.
- 使用 `谓词 + 名词` 命名.
- 注: 获取数据的方法统一以 `get` 开头.
- 为 `async` 异步函数.

其他的信息你应该可以从 `doc string` 里得到.

!!! warning "API 文档指路: [graia.ariadne][]"

## 获取实例所管账号

`Ariadne` 通过一个只读属性 `account` 来帮助用户获取当前机器人实例的 QQ 号

```python
account = app.account
```

## 方便的消息发送方法 - send_message

!!! note "这个方法其实不如直接在 `Group` `Friend` `Member` 上使用 `send_message` 更方便, 但是你可以使用 `action`."

`send_message` 有一个限制: 只能从传入对象推断 (不能直接传入 `int` 格式的 `target`)

但是它可以智能地从传入对象推断: `Friend` `Group` `Member` `MessageEvent` 这四个都是合适的传入对象.

`Friend` 发送好友消息, `Group` 发送群组消息, **而 `Member` 发送临时私聊消息**.

`MessageEvent` 则会推断是 `GroupMessage`, `FriendMessage` 还是 `TempMessage`, 并自动发给对应的对象.

同时, 在向 `target` 传入消息事件时, `quote` 可以简单地传入 `True` 以达到引用回复的效果.

`quote` 也接受 `Source` 与 `MessageChain` 对象.

### send_message 的 action

`sendMessage` 可以携带一个 `action` 参数,
它是一个 `graia.ariadne.typing.SendMessageAction` 对象, 需要实现以下方法:

- `param`: 处理传入的数据并进行加工 (可用于自动携带 `At` 等消息元素)

- `result`: 成功发送时调用, 作为最终返回用户的数据.

- `exception`: 发送时发生异常则会调用, 作为最终返回用户的数据.

`Ariadne` 在 `graia.ariadne.util.send` 内建了以下 `SendMessageAction`, 直接传入这些类即可.

- `Strict`: 发生异常时自动引发. (默认)

- `Bypass`: 发生异常时返回异常对象, 注意异常重生的问题.

- `Ignore`: 发生异常时返回 `None`.

- `Safe`: 在第一次尝试失败后先移除 `quote`,
之后每次失败时按顺序替换元素为其 `asDisplay`: `AtAll`, `At`, `Poke`, `Forward`, `MultimediaElement`
若最后还是失败 (`AccountMuted` 等), 则会引发原始异常 (通过传入 `ignore` 决定)

下面是示例:

```py
from graia.ariadne.util.send import Strict, Bypass, Ignore, Safe

act = Strict or Bypass or Ignore or Safe or Safe(ignore=False) or Safe(ignore=True) # 看你怎么选择

await app.send_message(origin, message_chain, action=act)
```

### 设置默认 action

`Ariadne` 实例的默认 `action` 是 `Strict`, 你可以通过 `Ariadne.default_send_action` 属性透明地修改.
