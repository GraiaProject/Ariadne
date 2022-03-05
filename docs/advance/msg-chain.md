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

与字符串对象一样, 消息链对象支持 `startswith`, `endswith`, `removeprefix`, `removesuffix` 四个方法.

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

### replace 方法

`MessageChain` 的 `replace` 方法与 `str` 的 `replace` 方法有异曲同工之妙.

在其表面下, `findSubChain` 承担了大部分工作, 找出所有符合 `old` 的部分, 之后由简单的循环完成替换.

```pycon
>>> MessageChain(["Hello World!Hello World!""How are you?", At(1), "yo"]).replace(
...     MessageChain(["Hello World!"]),
...     MessageChain(["No!"])
... )
MessageChain([Plain("No!No!How are you?"), At(1), Plain("yo")])
```

!!! note "提示"

    这对于 `At` 等元素也适用. 此外, `replace` 的 `old`, `new` 参数为 `MessageChain`, `Iterable[Element]`, `Element` 中一种即可.

    ```py
    msg.replace(At(app.account), Plain("[bot]"))
    ```

### join 方法

`MessageChain` 的 `join` 方法与 `str` 的 `join` 方法大致相同.

接受一个内容为 `MessageChain` 的可迭代对象, 并用其自身拼接.

`merge` 参数决定是否自动帮你拼接消息链, 默认为是.

```pycon
>>> MessageChain([" "]).join([MessageChain(["A"]), MessageChain(["B"]), MessageChain(["C"])])
MessageChain([Plain("A B C")])
>>> MessageChain([" "]).join([MessageChain(["A"]), MessageChain(["B"]), MessageChain(["C"])], merge=False)
MessageChain([Plain("A"), Plain(" "), Plain("B"), Plain(" "), Plain("C")])
```

## 元素安全性

因为 `MessageChain` 是一个可变对象, 其底层的 `Element` 属性可以被修改, 所以自然可以这样做:

```pycon
>>> chain = MessageChain([Plain("hello"), At(12345)])
>>> chain[1].target = 99999
>>> chain
MessageChain([Plain("hello"), At(99999)])
```

然后, 这样是 **预期行为** :

```pycon
>>> chain = MessageChain([Plain("Hello"), Plain("World"), At(12345)])
>>> merged = chain.merge()
>>> chain
MessageChain([Plain(text='HelloWorld'), At(target=12345)])
>>> merged[0].text = "test"
>>> chain
MessageChain([Plain(text='test'), At(target=12345)])
```

```pycon
>>> chain = MessageChain([Plain("Hello"), Plain("World"), At(12345)])
>>> merged = chain.merge(copy=True)
>>> chain
MessageChain([Plain(text='HelloWorld'), At(target=12345)])
>>> merged[0].text = "test"
>>> chain
MessageChain([Plain(text='HelloWorld'), At(target=12345)])
>>> merged
MessageChain([Plain(text='test'), At(target=12345)])
```

原因很简单, `Ariadne` 的 `MessageChain` 是支持链式调用的, 所以 **所有对消息链的操作都会返回一个消息链引用** .

自 `0.5.1` 起, 所有消息链的修改操作都支持布尔参数 `copy` (可能为仅关键字参数), `copy = True` 时会返回消息链的 **副本** (相当于在 `chain.copy()` 上操作),
否则会返回自身的引用.
