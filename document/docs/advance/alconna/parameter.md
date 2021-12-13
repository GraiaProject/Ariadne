# 参数一览

## 正则匹配

`Alconna` 提供了一些预制的正则表达式, 通常以 "Any" 打头

-   AnyStr: 任意字符
-   AnyDigit: 任意数字
-   AnyIP: 任意 ip
-   AnyUrl: 任意链接

当然，您可以填入自己的正则表达式

!!! warning "请不要在 `option` 与 `subcommand` 的 `name` 里填入正则表达式"

!!! quote "`args`的格式为 key-value, `key`是作为该参数的说明与查找的，在指令中不需要输入; `value`支持一般字符串、正则表达式与元素类型"

## Option

`Option` 是基础的选项类

```python
option = Option("name", key1=value1, key2=value2)
```

`Option` 需要两类参数

-   name: 该 `Option` 的名字，必填
-   args: 该 `Option` 可能的参数，选填，可选多个

当只填写了`name`时，`Alconna` 会默认该 `Option` 的参数为 Ellipsis (即"...")

## Subcommand

`Subcommand` 比起 `Option` 更类似于一个单独的 `Command`, 当然, 没有命令头

```python
subcommand = Subcommand("name", Option("option1"), Option("option2"), key1=value1, key2=value2)
```

`Subcommand` 需要三类参数

-   name: 该 `Option` 的名字，必填
-   Options: 该 `Subcommand` 可能的选项，选填，可选多个
-   args: 该 `Option` 可能的参数，选填，可选多个

当只填写了 `name` 时，`Alconna` 会默认该 `Subcommand` 的参数为 Ellipsis (即"...")

`Options` 为选项类的列表, 但注意不能嵌套 `Subcommand`
