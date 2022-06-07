# 基础消息链处理器

!!! info "提示"

    这里介绍的所有处理器都是 `Broadcast Decorator`.

    想知道更多关于 `Decorator` 的事可以点击 [这里](https://autumn-psi.vercel.app/docs/broadcast/basic/decorator).

本部分代码在 [`base.py`](https://github.com/GraiaProject/Ariadne/blob/master/src/graia/ariadne/message/parser/base.py)

不匹配时它们都会通过引发 `ExecutionStop` 停止执行.

## DetectPrefix

顾名思义, 检测前缀.

实例化时传入前缀 **字符串** 即可.

### 使用

作为 `Decorator`, 你应该放到 `broadcast.receiver` / `ListenerSchema` 的 `decorators` 参数列表里.

```py
@broadcast.receiver(..., decorators=[DetectPrefix('/')])
def on_message(chain: MessageChain): # chain 必定以 "/" 打头
    ...
```

或者也可以这样:

```py
async def foo_func(chain: MessageChain = DetectPrefix(".Test")): # 以这种形式使用, 发送的消息以 ".Test" 打头, 但收到时会被去除
    ... # ".TestSomething" -> "Something"
```

这会自动去掉前缀. 但是不会改动 `Quote` 与 `Source` 等元数据元素.


## DetectSuffix

顾名思义, 检测后缀.

实例化时传入后缀 **字符串** 即可.

### 使用

作为 `Decorator`, 放到 `broadcast.receiver` / `ListenerSchema` 的 `decorators` .

```py
@broadcast.receiver(..., decorators=[DetectSuffix('启动')])
def on_message(chain: MessageChain): # chain 必定以 "启动" 结尾
    ...
```

或者也可以这样:

```py
async def foo_func(chain: MessageChain = DetectSuffix("suffix")): # 以这种形式使用, 发送的消息以 "suffix" 结尾, 但收到时会被去除
    ... # "TestSuffix" -> "Test"

async def foo_func(chain: Annotated[MessageChain, DetectSuffix("suffix")]): ... # 等价于上面的写法
```

这会自动去掉后缀. 但是不会改动 `Quote` 与 `Source` 等元数据元素.

## MentionMe

检测在聊天中提到 Bot (At Bot 或以 Bot 群昵称/自己名称 打头).

### 使用

`Decorator`: 放到 `broadcast.receiver` / `ListenerSchema` 的 `decorators` .

```py
@broadcast.receiver(..., decorators=[MentionMe()]) # 注意要实例化
async def on_mention_me(chain: MessageChain): # 不会改动消息链
    ...
```

或者:

```py
async def foo_func(chain: MessageChain = MentionMe(target=...)):
    ... # 自动去除前面的 At 或名字


async def foo_func(chain: Annotated[MessageChain, MentionMe(target=...)]): ...# 等价于上面的写法
```

## Mention

检测在聊天中提到指定的人 (At 指定的人 或以 指定的人 群昵称/名称打头).

### 使用

`Decorator`: 放到 `broadcast.receiver` / `ListenerSchema` 的 `decorators` .

同时你需要为其提供 target 参数.

```py
@broadcast.receiver(..., decorators=[Mention(target=...)]) # target: int | str
# int: 用户 QQ 号, str: 用户的名字
async def on_mention(chain: MessageChain): # 不会改动消息链
    ...
```

或者:

```py
async def foo_func(chain: MessageChain = Mention(target=...)):
    ... # 自动去除前面的 At 或名字


async def foo_func(chain: Annotated[MessageChain, Mention(target=...)]): ...# 等价于上面的写法
```

## ContainKeyword

检测消息链是否包含指定关键字.

### 使用

`Decorator`: 放入 `broadcast.receiver` / `ListenerSchema` 的 `decorators` .

同时你需要为其提供 keyword 参数.

```py
@broadcast.receiver(..., decorators=[ContainKeyword(keyword=...)]) # keyword: str
async def on_contain_keyword(chain: MessageChain): # 不会改动消息链
    ...
```

## MatchContent

检测消息链是否与对应消息链相等.

!!! warning "注意 Image 等元素的特殊对比规则"

### 使用

`Decorator`: 放入 `broadcast.receiver` / `ListenerSchema` 的 `decorators` .

```py
@broadcast.receiver(..., decorators=[MatchContent(content=...)])
# content: str | MessageChain
# 当 content 为 str 时, 将会与MessageChain.asDisplay()进行比较, 当 content 为 MessageChain 时, 将会与 MessageChain 进行比较
async def on_match_content(chain: MessageChain): # 不会改动消息链
    ...
```

## MatchRegex

检测消息链是否匹配指定正则表达式.

!!! warning "注意 [] 等特殊字符, 因为是使用 `MessageChain.asDisplay` 结果作为匹配源的."

### 使用

`Decorator`: 放入 `broadcast.receiver` / `ListenerSchema` 的 `decorators` .

```py
@broadcast.receiver(..., decorators=[MatchRegex(regex=r"\d+")]) # regex 参数为 regex 表达式
async def on_match_regex(chain: MessageChain): # 不会改动消息链
    ...
```

## MatchTemplate

检测消息链是否匹配指定模板.

遇到元素实例则检测是否相等，遇到元素类型则检测类型是否匹配.

`Plain` 实例与类型会被自动拼接起来.

### 使用

`Decorator`: 放入 `broadcast.receiver` / `ListenerSchema` 的 `decorators` .

```py
@broadcast.receiver(..., decorators=[MatchTemplate([Plain, Plain("搜图"), Image])]) # 需要 "*搜图 [图片]" 才能匹配 (*为任意多字符)
async def on_match(chain: MessageChain): # 不会改动消息链
    ...
```

## FuzzyMatch

模糊匹配字符串.

### 使用

`Decorator`: 放入 `broadcast.receiver` / `ListenerSchema` 的 `decorators` .

```py
@broadcast.receiver(..., decorators=[FuzzyMatch("github"))]) # 默认阈值为 60% 相似
async def on_match(chain: MessageChain): # 不会改动消息链
    ...
```

!!! warning "我们更推荐 FuzzyDispatcher, 因为它只在多个匹配中选择最相近的一个."

## FuzzyDispatcher

模糊匹配字符串.

### 使用

作为 `Dispatcher` 使用. 在相同 `scope` 中只有最相近的匹配会被激活.

```py
@broadcast.receiver(..., dispatchers=[FuzzyDispatcher("github"))]) # 默认阈值为 60% 相似
async def on_match(chain: MessageChain, rate: float): # 若要获取相似度必须包含 "rate" 单词
    ...

@broadcast.receiver(..., dispatchers=[FuzzyDispatcher("gitlab"))]) # 与上面的默认不能同时触发
async def on_match(chain: MessageChain):
    ...
```

!!! graiax "社区文档相关章节: [链接](https://graiax.cn/guide/base_parser.html)"
