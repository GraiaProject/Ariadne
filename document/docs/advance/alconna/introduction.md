# 介绍

## Alconna 是什么?

[`Alconna`](https://github.com/RF-Tar-Railt/Cesloi-Alconna) 是 `Arclet` 下的命令解析器, 现属于 `Cesloi`

`Alconna` 可以通过单个对象去解析多种命令

`Alconna` 提供了简单的构造方法, 无需调整过多参数便可使用; 可以解析字符串与消息链

`Alconna` 会将解析的结果包装成 `Arpamar`, 你可以通过 `Arpamar` 获取传入的消息内容

```python
>>> from alconna import *
>>> v = Alconna(headers=["!", ".bot"], command=f"获取{AnyStr}的涩图")
>>> v.analyse_message("!获取円香的涩图").header
'円香'
```

## 前身

`Alconna` 的前身是 [`Cesloi-CommandAnalysis`](https://github.com/RF-Tar-Railt/Cesloi-CommandAnalisys)

相比 `Alconna`, `CommandAnalysis` 结构更加简单, 但遗憾的是只能解析字符串命令

```python
>>> from command import *
# 与上面Alconna的对比
>>> v = Command(headers=[""], main=["img", [["download", ["-p", AnyStr]], ["upload", [["-u", AnyStr], ["-f", AnyStr]]]]])
>>> v.analysis("img upload -u http://www.baidu.com")
'http://www.baidu.com'
>>> v.analysis("img upload -f img.png")
'img.png'
```

> 为什么提起 CommandAnalysis？

别急，接着往下看

## 命令的结构

我们假设一条命令为

```
sdist upload -r pypi
```

当我们以 json 结构去表示这个命令时, 有大致两种结构:

`"_upload_"`, 下划线表示该处为`single-str-match`, 即参数只能为 **指定字符串**

`"%pypi%"`, 百分号表示该处为`any-str-match`, 即参数可以为 **任意字符串**

```json
a = {
  "main": {
    "name": "sdist",
    "separate": " ",
    "args": [
      " _upload_ "
    ]
  },
  "separate": " ",
  "subcommand": [
    {
      "name": "-r",
      "separate": " ",
      "args": " %pypi% "
    }
  ]
}

b = {
  "name": "sdist",
  "separate": " ",
  "args": [
    {
      "name": "upload",
      "separate": " ",
      "args": [
        {
          "name": "-r",
          "separate": " ",
          "args": " %pypi% "
        }
      ]
    }
  ]
}
```

显然的是，第一种结构的层数更少，第二种结构的拓展性更好

而 `CommandAnalysis` 正是根据第二种结构实现的命令解析

让我们来看 `CommandAnalysis` 的构造方法:

```python
Command(headers=[""], main=["name", "args/subcommand/subcommand_list", "separate"])
```

其中

-   headers: 呼叫该命令的命令头列表
-   name: 命令名称
-   args: 命令参数
-   separate: 命令分隔符,分隔 name 与 args,通常情况下为 " " (空格)
-   subcommand: 子命令, 格式与 main 相同
-   subcommand_list: 子命令集, 可传入多个子命令

在这里，我们将一个命令抽象为两个部分, 即 **命令头(headers)** 与 **命令主体(main)**

命令头常见的有 斜杠"/", 半角句号".", 感叹号"!", 全角句号"。" 等等，是作为区分平常语句与命令的 **唯一标识符**

命令主体也可以抽象为三个部分, 即 **名称(name)**, **参数(args)** 和 **分隔符(separate)**

以常见命令 `/ping 127.0.0.1` 为例,

`/` 是命令头, `ping` 是命令名称, `空格` (`\x20`) 是命令分隔符, `127.0.0.1` 是命令参数

以 json 表示就是

```json5
{
    header: "/",
    main: {
        name: "ping",
        separate: " ",
        args: "127.0.0.1",
    },
}
```

那么怎么转换成可以让解析器解析的命令呢？

只需要这么写:

```python
Command(headers=["/"], main=["ping", AnyIP])
```

AnyIP 其实是预制的正则表达式。是的，在 `CommandAnalysis` 中, 你可以在任意地方写入自己的正则表达式。

> 所以提这些是干什么呢？

读完这些，你应该对 **命令(Command)** 的结构有一个大致的了解, 这也是为后面你学习的 `Alconna` 做功课

接下来, 便是对于 `Alconna` 的详细介绍了.

## 性能参考

在 i5-10210U 处理器上, `Alconna` 的性能大约为 `36000~41000 msg/s`, 取决于 `Alconna` 的复杂程度.

## 与 Twilight 对比

`Twilight` 偏重于对消息链的正则化处理,

而 `Alconna` 偏重于对参数的各种形式解析 (更像 `argparse` 模块).

如果你想要 `argparse` 中各种特别 `Action` (如 `append`) 的原生支持, 可能 `Twilight` 会更好编写. (而且 `Twilight` 还自带帮助生成器)

但是 `Alconna` 有子命令的支持, 且性能占优.

总之, 根据自己的需要, 选择合适的工具.

!!! quote

    There should be one-- and preferably only one --obvious way to do it.

    The Zen of Python
