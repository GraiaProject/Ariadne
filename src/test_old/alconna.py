from arclet.alconna import Alconna, Args
from arclet.alconna.component import Subcommand, Option, Arpamar
from arclet.alconna.types import AnyUrl, AnyIP, AnyDigit, AnyStr, AllParam, AnyParam

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Source, Face


ar = Args["test":bool:True]["aaa":str:"bbb"] << Args["perm":str:...] + ["month", int]
a = "bbb"
b = str
c = "fff"
ar["foo"] = ["bar", ...]
ar.foo1 = ("bar1", "321")
print(ar)

ping = Alconna(
    headers=["/", "!"],
    command="ping",
    options=[
        Subcommand(
            "test", Option("-u", Args["username":str]).help("输入用户名"), args=Args["test":"Test"]
        ).separate(' ').help("测试用例"),
        Option("-n|--num", Args["count":int:123]).help("输入数字"),
        Option("-u", Args(At=At)).help("输入需要At的用户")
    ],
    main_args=Args(IP=AnyIP)
).help("ping指令")
print(ping.get_help())
msg = MessageChain.create("/ping -u", At(123), "test Test -u AAA -n 222 127.0.0.1")
print(msg)
print(ping.analyse_message(msg))

msg1 = MessageChain.create("/ping 127.0.0.1 -u", At(123))
print(msg1)
print(ping.analyse_message(msg1).all_matched_args)

msg2 = MessageChain.create("/ping a")
print(msg2)
result = ping.analyse_message(msg2)
print(result.header)
print(result.head_matched)

pip = Alconna(
    command="/pip",
    options=[
        Subcommand("install", Option("--upgrade").help("升级包"), pak=str).help("安装一个包"),
        Subcommand("show", pak=str).help("显示一个包的信息"),
        Subcommand("help", command=str).help("显示一个指令的帮助"),
        Option("list").help("列出所有安装的包"),
        Option("--retries", retries=int).help("设置尝试次数"),
        Option("-t| --timeout", sec=int).help("设置超时时间"),
        Option("--exists-action", ex_action=str).help("添加行为"),
        Option("--trusted-host", hostname=AnyUrl).help("选择可信赖地址")
    ]
).help("pip指令")
print(pip.get_help())
msg = "/pip install ces --upgrade -t 6 --trusted-host http://pypi.douban.com/simple"
print(msg)
print(pip.analyse_message(msg).all_matched_args)

aaa = Alconna(headers=[".", "!"], command="摸一摸", main_args=Args["At":At])
msg = MessageChain.create(".摸一摸", At(123))
print(msg)
print(aaa.analyse_message(msg).matched)

ccc = Alconna(
    headers=[""],
    command="4help",
    main_argument=AnyStr
)
msg = "4help 'what he say?'"
print(msg)
result = ccc.analyse_message(msg)
print(result.main_argument)

eee = Alconna(
    headers=[""],
    command=f"RD{AnyDigit}?=={AnyDigit}"
)
msg = "RD100==36"
result = eee.analyse_message(msg)
print(result.header)

weather = Alconna(
    headers=['渊白', 'cmd.', '/bot '],
    command=f"{AnyStr}天气",
    options=[
        Option("时间")["days":str, "aaa":str].separate('='),
        Option("bbb")
    ]
)
msg = MessageChain.create('渊白桂林天气 时间=明天=后台 bbb')
result = weather.analyse_message(msg)
print(result)
print(result['aaa'])

msg = MessageChain.create('渊白桂林天气 aaa')
result = weather.analyse_message(msg)
print(result)

msg = MessageChain.create(At(123))
result = weather.analyse_message(msg)
print(result)

ddd = Alconna(
    command="Cal",
    options=[
        Subcommand(
            "-div",
            Option(
                "--round| -r",
                args=Args(decimal=AnyDigit),
                actions=lambda x: x + "a"
            ).help("保留n位小数"),
            args=Args(num_a=AnyDigit, num_b=AnyDigit)).help("除法计算")
    ],
)
msg = "Cal -div 12 23 --round 2"
print(msg)
print(ddd.get_help())
result = ddd.analyse_message(msg)
print(result.div)

ddd = Alconna(
    command="点歌"
).option(
    "歌名", sep="：", args=Args(song_name=AnyStr)
).option(
    "歌手", sep="：", args=Args(singer_name=AnyStr)
)
msg = "点歌 歌名：Freejia"
print(msg)
result = ddd.analyse_message(msg)
print(result.all_matched_args)

give = Alconna.simple("give", ("sb", int, ...), ("sth", int, ...))
print(give)
print(give.analyse_message("give"))


def test_act(content):
    print(content)
    return content


wild = Alconna(
    headers=[At(12345)],
    command="丢漂流瓶",
    main_args=Args["wild":AnyParam],
    actions=test_act
)
# print(wild.analyse_message("丢漂流瓶 aaa bbb ccc").all_matched_args)
msg = MessageChain.create(At(12345), " 丢漂流瓶 aa\t\nvv")
print(wild.analyse_message(msg))

get_ap = Alconna(
    command="AP",
    main_args=Args(type=str, text=str)
)

test = Alconna(
    command="test",
    main_args=Args(t=Arpamar)
).set_namespace("TEST")
print(test)
print(test.analyse_message(
    [get_ap.analyse_message("AP Plain test"), get_ap.analyse_message("AP At 123")]
).all_matched_args)

# print(command_manager.commands)

double_default = Alconna(
    command="double",
    main_args=Args(num=int).default(num=22),
    options=[
        Option("--d", Args(num1=int).default(num1=22))
    ]
)


result = double_default.analyse_message("double --d")
print(result)


alc4 = Alconna(
    command="test_multi",
    options=[
        Option("--foo", Args["*tags":int:1, "str1":str]),
        Option("--bar", Args["num": int]),
    ]
)

print(alc4.analyse_message("test_multi --foo 1 2 3 4 ab --bar 1"))
alc4.shortcut("st", "test_multi --foo 1 2 3 4 ab --bar 1")
print(alc4.analyse_message("st"))

choice = Alconna(
    command="choice",
    main_args=Args["part":["a", "b", "c"]]
)
print(choice.analyse_message("choice d"))
print(choice.get_help())


