# 消息链: 进阶

### subchain 方法

`MessageChain.subchain` 是这样使用的:

传入一个 `slice` 切片对象, 其 `start` 与 `stop` (可选) 均为 **二元组**, 为 `(int, Optional[int]` 格式.

切片对象 `start` 与 `stop` 的第一个整数指示元素起止位置. (含义同在序列上切片)

若有第二个整数, 则分别指示 **开头文本起始下标** 与 **末尾文本结束下标**. (含义同在字符串上切片)

示例:

```python
assert (MessageChain.create("hello world"))[(0,3):(1,7)] == MessageChain([Plain(text='lo w')])
```

!!! warning "注意"

    若提供第二个整数时 首/尾 元素不为文本则会引发 `ValueError`.

???+ note "提示"

    在消息链对象上使用 `[]` 符号并使用 `MessageChain[(a1, a2):(b1, b2)]`

    相当于调用 `MessageChain.subchain(slice((a1, a2), (b1, b2)))`

### 筛选元素

使用 `include` 与 `exclude` 方法可以筛选消息链中的元素.

```py
msg_chain = MessageChain.create("Hello", At(target=12345))
assert msg_chain.include(Plain) == MessageChain([Plain(text='Hello')])
assert msg_chain.exclude(Plain) == MessageChain([At(target=12345)])
```

### 分割

使用 `split` 方法以切割消息链为 **多个消息链**.

`raw_string` 参数用于指示是否要保留 "空" 的文本元素.

```py
msg_chain = MessageChain.create("Hello world!", At(target=12345))
assert msg_chain.split("world!", raw_string=True) == [MessageChain([Plain(text='Hello ')]), MessageChain([Plain(text=''), At(target=12345)])]
assert msg_chain.split("world!") == [MessageChain([Plain(text='Hello ')]), MessageChain([At(target=12345)])]
```

### 前缀与后缀操作

与字符串对象一样, 消息链对象支持 `startswith`, `endswith`, `removeprefix` `removesuffix` 四个方法.

!!! warning "注意"

    消息链在执行这些方法时 **不会去掉其他元素**.

```py
msg_chain = MessageChain.create("Hello world!", At(target=12345))
assert msg_chain.removeprefix("Hello") == MessageChain([Plain(text=' world!'), At(target=12345)])
assert msg_chain.removesuffix("world!") == MessageChain([Plain(text='Hello world!'), At(target=12345)])
assert not msg_chain.endswith("world!")
```

???+ info "提示"

    `removeprefix` 方法有一个额外的 `skip_header` 参数, 可以跳过 `Source` 与 `Quote` 进行操作 (并在最后放回消息链).

???+ info "又及"

    你知道的, `Python` 在 3.9 以后才正式引入 `removeprefix` 与 `removesuffix` 方法......

    不过 `Ariadne` 中的这两个方法并不需要 `Python` 3.9+

### 映射字符串

映射字符串部分解决了 `MessageChain` 与 `str` 的互操作性问题. 其核心思想为 将 `Element` 看作一个特殊的字符序列.

```python
msg_chain = MessageChain.create("Hello world!", At(target=12345))
assert msg_chain.asMappingString() == ('Hello world!\x021_At\x03', {1: At(target=12345)})
```

为了明确的分开元素与常规文本, 我们使用 `\x02(\\d+)_(\\w+)\x03` 的正则表达式标记元素.

!!! info "这是一个 Python 的正常字符串, 而非原始字符串 (r-string)."

`(\\d+)` 部分代表的是字典中的 `key`, 可以通过这种方式提取对应的元素.

`(\\w+)` 代表的是本元素的类型, 可以利用其检查元素类型是否正确.

!!! note "这个特性在 [Twilight](./twilight.md) 中被使用."

在完成操作后 (当然不能破坏元素标记的结构), 可以利用 `MessageChain.fromMappingString` 方法构造原来的消息链.

```py
msg_chain = MessageChain.create("Hello world!", At(target=12345))
string, mapping = msg_chain.asMappingString()
new_string = string.removeprefix("Hello world") # new_string = "!\x021_At\x03"
assert MessageChain.fromMappingString(new_string, mapping) == MessageChain([Plain(text='!'), At(target=12345)])
```

!!! example "又及"

    `MessageChain.asMappingString` 有以下参数:

    - remove_source (bool, optional): 是否移除消息链中的 Source 元素. 默认为 True.
    - remove_quote (bool, optional): 处理时是否要移除消息链的 Quote 元素. 默认为 True.
    - remove_extra_space (bool, optional): 是否移除 Quote At AtAll 的多余空格. 默认为 False.