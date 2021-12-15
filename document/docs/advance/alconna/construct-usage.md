# 构造与使用

!!! info "在阅读本部分以前, 确保您已阅读关于命令结果的部分"

## 结构

一个 `Alconna` 实例的结构如下:

```python
Alconna(
    headers=["command_head"],
    command="command_name",
    options=[
        Subcommand(
            "sub_name",
            Option(
                "sub_opt_name",
                sub_opt_arg=sub_opt_arg
            ),
            sub_main_arg=sub_main_arg
        ),
        Option(
            "opt_name",
             opt_arg=opt_arg
        )
    ]
    main_argument=main_argument
)
```

`Alconna`支持四大类参数：

-   `headers` : 呼叫该命令的命令头，一般是你的机器人的名字或者符号，与 `command` 至少有一个填写. 例如: /, !
-   `command` : 命令名称，你的命令的名字，与 `headers` 至少有一个填写
-   `options` : 命令选项，你的命令可选择的所有 `option`,是一个包含 `Subcommand` 与 `Option` 的列表
-   `main_argument` : 主参数，填入后当且仅当命令中含有该参数时才会成功解析

其中

-   command_head: 命令头
-   command_name: 命令名称
-   sub_name: 子命令名称
-   sub_opt_name: 子命令选项名称
-   sub_opt_arg: 子命令选项参数
-   sub_main_arg: 子命令主参数
-   opt_name: 命令选项名称
-   opt_arg: 命令选项参数

解析时，先判断命令头(即 headers + command), 再判断 options 与 main argument, 这里 options 与 main argument 在输入指令时是不分先后的

## 使用

现在，我们假设一命令如下:

```
/pip
Usage:
  /pip <command> [options]

Commands:
  install                     Install packages.
  list                        List installed packages.
  show                        Show information about installed packages.
  help                        Show help for commands.

General Options:
  --help                      Show help.
  --retries <retries>         Maximum number of retries each connection should attempt (default 5 times).
  --timeout <sec>             Set the socket timeout (default 15 seconds).
  --exists-action <action>    Default action when a path already exists: (s)witch, (i)gnore, (w)ipe, (b)ackup, (a)bort.
  --trusted-host <hostname>   Mark this host or host:port pair as trusted, even though it does not have valid or any HTTPS.
```

根据上述的 Alconna 结构与前文的命令结构分析，我们可以得到这样的 `Alconna`:

```python
pip = Alconna(
    command="/pip",
    options=[
        Subcommand(
            "install",
            Option("--upgrade"),
            pak=AnyStr,
        ),
        Subcommand(
            "show",
            pak=AnyStr,
        ),
        Subcommand(
            "help",
            command=AnyStr,
        ),
        Option("list"),
        Option("--help"),
        Option("--retries", retries=AnyDigit),
        Option("--timeout", sec=AnyDigit),
        Option("--exists-action", action=AnyStr),
        Option("--trusted-host", hostname=AnyUrl)
    ]
)
```

现在你可以尝试如下输入:

```
>>> pip.analyse_message("/pip install cesloi --upgrade --trusted-host http://pypi.douban.com/simple").option_args
```

正常情况下, 会输出：

```
{'upgrade': Ellipsis, 'pak': 'cesloi', 'hostname': 'http://pypi.douban.com/simple'}
```
