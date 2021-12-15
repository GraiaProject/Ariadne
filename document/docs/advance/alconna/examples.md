# 示例

## 奇奇怪怪的命令

`Alconna` 的 `command` 支持写入正则表达式, 所以以下命令是可以的

```python
>>> w = Alconna(command=f"查询{AnyStr}天气")
>>> d = Alconna(headers=["."], command=f"d{AnyDigit}")
>>> w.analyse_message("查询北京天气").header
'北京'
>>> d.analyse_message(".d100").header
'100'
```

## 选项的多参数

`Option` 与 `Subcommand` 的 `args` 可以填入不止一个参数，所以以下命令是可以的

```python
>>> cal = Alconna(command="Cal",options=[Option("-sum", num_a=AnyDigit, num_b=AnyDigit)])
>>> msg = "Cal -sum 12 23"
>>> cal.analyse_message(msg).get('sum')
{'num_a': '12', 'num_b': '23'}
>>> cal = Alconna(command="Cal",options=[Subcommand("-div", Option("--round", decimal=AnyDigit), num_a=AnyDigit, num_b=AnyDigit)])
>>> msg = "Cal -div 12 23 --round 2"
>>> cal.analyse_message(msg).get('div')
{'num_a': '12', 'num_b': '23', 'round': {'decimal': '2'}}
```

> P.S. Alconna 在解析完成后会把 横杠("-") 给过滤掉

## 自定义分隔符

`Alconna` 不强制 shell-like 的指令，所以以下命令是可以的

```python
>>> music = Alconna(
...     headers=["!"],
...     command="点歌",
...     options=[
...         Option("歌名", song_name=AnyStr).separate(':'),
...         Option("歌手", singer_name=AnyStr).separate(':')
...     ]
... )
>>> music.analyse_message("!点歌 歌名:Freejia").option_args
{'song_name': 'Freejia'}
```

> P.S. 如果你想用空字符串作为分隔符的话,为什么不试试第一种写法呢？
