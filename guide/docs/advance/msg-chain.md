# 消息链: 进阶

## subchain 方法

`MessageChain.subchain` 是这样使用的:

传入一个 `slice` 切片对象, 其 `start` 与 `stop` (可选) 均为 **二元组**, 为 (int, Optional[int]) 格式.

切片对象 `start` 与 `stop` 的第一个整数指示元素起止位置. (含义同在序列上切片)

若有第二个整数, 则分别指示 **开头文本起始下标** 与 **末尾文本结束下标**. (含义同在字符串上切片)

示例:

```python
>>> (MessageChain.create("hello world"))[(0,3):]
MessageChain([Plain(text='lo world')])

>>> (MessageChain.create("hello world"))[:(1,7)]
MessageChain([Plain(text='hello w')])

>>> (MessageChain.create("hello world"))[(0,3):(1,7)]
MessageChain([Plain(text='lo w')])
```

!!! warning "注意"

    若提供第二个整数时 首/尾 元素不为文本则会引发 `ValueError`.

!!! note "提示"

    在消息链对象上使用 `[]` 符号并使用 `MessageChain[(a1, a2):(b1, b2)]`

    相当于调用 `MessageChain.subchain(slice((a1, a2), (b1, b2)))`
