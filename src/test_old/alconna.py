from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At
from graia.ariadne.message.parser.alconna import Alconna, AnyDigit, AnyStr, Option

"""ping = Alconna(
    headers=["/", "!"],
    command="ping",
    options=[
        Subcommand(
            "test",
            Option("-u", username=AnyStr)
        ).separate(' '),
        Option("-n", count=AnyDigit),
        Option("-t"),
        Option("-u", At=At)
    ],
    main_argument=AnyIP
)
msg = MessageChain.create("/ping -u", At(123), "test -u AAA -n 222 127.0.0.1")
print(msg)
print(ping.analysis_message(msg).results)
msg1 = MessageChain.create("/ping 127.0.0.1 -u", At(123))
print(msg1)
print(ping.analysis_message(msg1).has('u'))
msg2 = MessageChain.create("/ping")
print(msg2)
result = ping.analysis_message(msg2)
print(result.matched)
"""
aaa = Alconna(headers=[".", "!"], command="摸一摸", main_argument=At)
msg = MessageChain.create(".摸一摸", At(123))
print(msg)
print(aaa.analyse_message(msg).matched)
"""
img = Alconna(
    headers=[".", "。"],
    command="Image",
    options=[
        Subcommand(
            "upload",
            Option("-path", path=AnyStr),
            Option("-image", image=Image),
        ),
        Subcommand(
            "download",
            Option("-url", url=AnyUrl)
        ),
        Option("--savePath", path=AnyStr)
    ]
)
msg = MessageChain.create("。Image --savePath test.png upload -image ",
                            Image(path="alconna.png"), " download -url https://www.baidu.com")
print(msg.to_text())
print(img.analysis_message(msg).get('upload'))
ccc = Alconna(
    headers=[""],
    command="help",
    main_argument=AnyStr
)
msg = "help \"what he say?\""
print(msg)
result = ccc.analysis_message(msg)
print(result.main_argument)
ddd = Alconna(
    headers=[""],
    command=f"Cal",
    options=[
        Option("-sum", a=AnyDigit, b=AnyDigit)
    ]
)
msg = "Cal -sum 12 23"
print(msg)
result = ddd.analysis_message(msg)
print(result.get('sum'))
"""
ddd = Alconna(
    headers=[""],
    command="点歌",
    options=[Option("歌名", song_name=AnyStr).separate("："), Option("歌手", singer_name=AnyStr).separate("：")],
)
msg = "点歌 歌名：Freejia"
print(msg)
result = ddd.analyse_message(msg)
print(result.matched)

eee = Alconna(headers=[""], command=f"RD{AnyDigit}?=={AnyDigit}")
msg = "RD100==36"
result = eee.analyse_message(msg)
print(result.results)
"""
print(Alconna.split("Hello! \"what is it?\" aaa bbb"))"""

weather = Alconna(
    headers=["渊白", "cmd.", "/bot "], command=f"{AnyStr}天气", options=[Option("时间", days=AnyStr).separate("=")]
)
msg = MessageChain.create("渊白桂林天气 时间=明天")
result = weather.analyse_message(msg)
print(result)

msg = MessageChain.create("渊白桂林天气")
result = weather.analyse_message(msg)
print(result)

msg = MessageChain.create("?")
result = weather.analyse_message(msg)
print(result)
