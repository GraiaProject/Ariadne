import base64

import aiohttp
import pytest

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import (
    At,
    AtAll,
    BaseText,
    Element,
    Image,
    Plain,
    Quote,
    Source,
)
from graia.ariadne.util import Dummy

__name__ = "graia.test.message.chain"  # monkey patch to pass internal class check


def test_create():
    chain = MessageChain([Plain("Hello World"), At(12345), Plain("1234567")])
    assert (
        MessageChain("Hello World", [At(12345)], MessageChain([Plain("1234567")])).__root__ == chain.__root__
    )
    assert MessageChain.parse_obj(
        [{"type": "At", "target": 12345}, {"type": "Plain", "text": "hello"}, {"type": "Broken"}, 5]
    ) == MessageChain([At(12345), "hello"])


def test_include_exclude():
    msg_chain = MessageChain("Hello", At(target=12345))
    assert msg_chain.include(Plain) == MessageChain([Plain(text="Hello")])
    assert msg_chain.exclude(Plain) == MessageChain([At(target=12345)])


def test_safe_display():
    msg_chain = MessageChain("Hello", At(target=12345))
    assert msg_chain.safe_display == "Hello@12345"
    assert "{chain.safe_display}".format(chain=msg_chain) == "Hello@12345"


def test_split():
    msg_chain = MessageChain("Hello world!", At(target=12345))
    assert msg_chain.split("world!", raw_string=True) == [
        MessageChain([Plain(text="Hello ")]),
        MessageChain([Plain(text=""), At(target=12345)]),
    ]
    assert msg_chain.split("world!") == [
        MessageChain([Plain(text="Hello ")]),
        MessageChain([At(target=12345)]),
    ]

    assert msg_chain.split(" ") == [
        MessageChain([Plain(text="Hello")]),
        MessageChain([Plain("world!"), At(target=12345)]),
    ]
    assert MessageChain(["hello world"]).split() == [MessageChain(["hello"]), MessageChain(["world"])]
    assert MessageChain(["hello "]).split() == [MessageChain(["hello"])]


def test_prefix_suffix():
    msg_chain = MessageChain("Hello world!", At(target=12345))
    assert msg_chain.removeprefix("Hello") == MessageChain([Plain(text=" world!"), At(target=12345)])
    assert msg_chain.removesuffix("world!") == MessageChain([Plain(text="Hello world!"), At(target=12345)])
    assert MessageChain(["hello world"]).removesuffix("world") == MessageChain([Plain("hello ")])
    assert not msg_chain.endswith("world!")
    assert not msg_chain.startswith("world!")
    assert msg_chain.startswith("Hello")

    assert MessageChain(["hello world"]).endswith("world")

    assert not MessageChain([At(12345), "hello"]).startswith("hello")


def test_has():
    msg_chain = MessageChain("Hello", At(target=12345))
    assert msg_chain.has(MessageChain([Plain(text="Hello")]))
    assert not msg_chain.has(MessageChain([Plain(text="LOL")]))
    assert msg_chain.has(At(target=12345))
    assert not msg_chain.has(At(target=12152))
    assert msg_chain.has("Hello")
    assert msg_chain.has(msg_chain)
    assert msg_chain.has(Plain)
    assert not msg_chain.has(Quote)
    assert msg_chain.find_sub_chain(MessageChain(["Hello"])) == [0]
    assert msg_chain.find_sub_chain(MessageChain(["Hello system"])) == []
    assert msg_chain.find_sub_chain(MessageChain(["HeHeHe"])) == []
    assert MessageChain(["HeHe"]).find_sub_chain(MessageChain(["HeHeHe"])) == []
    assert MessageChain(["HeHeHeHe"]).find_sub_chain(MessageChain(["HeHeHe"])) == [0, 2]
    assert MessageChain(["HeHeHaHaHoHo"]).find_sub_chain(MessageChain(["HeHeHoHo"])) == []


def test_contain():
    msg_chain = MessageChain("Hello", At(target=12345))
    assert MessageChain([Plain(text="Hello")]) in msg_chain
    assert At(target=12345) in msg_chain
    assert At(target=12152) not in msg_chain
    assert msg_chain.has("Hello")
    assert msg_chain in msg_chain


def test_get():
    msg_chain = MessageChain("Hello World!", At(target=12345), "Foo test!")
    assert msg_chain[Plain] == [Plain("Hello World!"), Plain("Foo test!")]
    assert msg_chain[Plain, 1] == [Plain("Hello World!")]
    assert msg_chain[1] == At(target=12345)
    assert msg_chain[:2] == MessageChain(["Hello World!", At(target=12345)])
    with pytest.raises(NotImplementedError):
        msg_chain["trial"]
    assert msg_chain.get(Plain) == msg_chain[Plain]
    assert msg_chain.get(Plain, 1) == msg_chain[Plain, 1]
    assert msg_chain.get_one(Plain, 0) == Plain("Hello World!")
    assert msg_chain.get_one(Plain, 1) == Plain("Foo test!")
    assert msg_chain.get_first(Plain) == Plain("Hello World!")


def test_only_contains():
    msg_chain = MessageChain("Hello World!", At(target=12345), "Foo test!")
    assert msg_chain.only(Plain, At)


def test_as_sendable():
    msg_chain = MessageChain(
        Source(id=1, time=12433531),
        Quote(id=41342, groupId=1234, senderId=123421, targetId=123422, origin=MessageChain("Hello")),
        "  hello!",
    )
    assert not msg_chain.only(Plain)
    assert msg_chain.as_sendable().__root__ != msg_chain.__root__
    assert msg_chain.as_sendable().only(Plain)


def test_persistent():
    msg_chain = MessageChain(
        Source(id=1, time=12433531),
        Quote(id=41342, groupId=1234, senderId=123421, targetId=123422, origin=MessageChain("Hello")),
        "hello!",
        At(12345),
    )
    assert msg_chain.as_persistent_string() == 'hello![mirai:At:{"target":12345}]'
    assert MessageChain.from_persistent_string('hello![_[mirai:At:{"target":12345}]') == MessageChain(
        ["hello![", At(12345)]
    )
    assert msg_chain.as_persistent_string(include=[At]) == '[mirai:At:{"target":12345}]'
    assert msg_chain.as_persistent_string(exclude=[At]) == "hello!"
    with pytest.raises(ValueError):
        msg_chain.as_persistent_string(include=[Plain], exclude=[Quote])
    multimedia_msg_chain = MessageChain(
        ["image:", Image(url="https://foo.bar.com/img.png", data_bytes=b"abcdef2310123asd")]
    )
    b64 = base64.b64encode(b"abcdef2310123asd").decode()
    assert (
        multimedia_msg_chain.as_persistent_string()
        == f'image:[mirai:Image:{{"url":"https://foo.bar.com/img.png","base64":"{b64}"}}]'
    )
    assert (
        multimedia_msg_chain.as_persistent_string(binary=False)
        == f'image:[mirai:Image:{{"url":"https://foo.bar.com/img.png"}}]'
    )


@pytest.mark.asyncio
async def test_download():
    url = "https://avatars.githubusercontent.com/u/67151942?s=200&v=4"
    chain = MessageChain(["text", Image(url=url)])
    from asyncio import Event, create_task

    from graia.amnesia.builtins.aiohttp import AiohttpService
    from launart import Launchable

    from graia.ariadne.app import Ariadne

    Ariadne._ensure_config()
    srv = AiohttpService()
    Ariadne.launch_manager.add_service(srv)

    class L(Launchable):
        id = "test_download"

        @property
        def stages(self):
            return {"blocking"}

        @property
        def required(self):
            return {"http.universal_client"}

        async def launch(self, _):
            async with self.stage("blocking"):
                await chain.download_binary()
                assert (
                    base64.b64decode(chain.get_first(Image).base64)
                    == await (await srv.session.get(url)).content.read()
                )

    Ariadne.launch_manager.add_launchable(L())
    await Ariadne.launch_manager.launch()


def test_presentation():
    msg_chain = MessageChain("Hello World!", At(target=12345), "Foo test!\n")
    assert msg_chain.display == "Hello World!@12345Foo test!\n"
    assert str(msg_chain) == msg_chain.display
    print(repr(msg_chain))
    assert (
        repr(msg_chain)
        == "MessageChain([Plain(text='Hello World!'), At(target=12345), Plain(text='Foo test!\\n')])"
    )
    assert eval(repr(msg_chain)) == msg_chain
    assert msg_chain.safe_display == "Hello World!@12345Foo test!\\n"


def test_magic():
    msg_chain = MessageChain("Hello world!", At(target=12345))
    for e in msg_chain:
        assert isinstance(e, Element)

    assert MessageChain(["Hello"]) == ["Hello"]
    assert MessageChain(["hello"]) == MessageChain("hello")

    assert MessageChain(["Hello World!"]) + MessageChain(["Goodbye World!"]) == MessageChain(
        [Plain("Hello World!"), Plain("Goodbye World!")]
    )
    assert MessageChain(["Hello World!"]) + [Plain("Goodbye World!")] == MessageChain(
        [Plain("Hello World!"), Plain("Goodbye World!")]
    )
    assert MessageChain(["Hello World!"]) * 2 == MessageChain([Plain("Hello World!"), Plain("Hello World!")])

    msg_chain = MessageChain("Hello World!")
    msg_chain *= 2
    assert msg_chain == MessageChain([Plain("Hello World!"), Plain("Hello World!")])
    msg_chain += [Plain("How are you?")]
    assert msg_chain == MessageChain([Plain("Hello World!"), Plain("Hello World!"), Plain("How are you?")])
    assert len(msg_chain) == 3

    msg_chain = MessageChain("Hello World!")
    msg_chain *= 2
    assert msg_chain == MessageChain([Plain("Hello World!"), Plain("Hello World!")])
    msg_chain += MessageChain([Plain("How are you?")])
    assert msg_chain == MessageChain([Plain("Hello World!"), Plain("Hello World!"), Plain("How are you?")])
    assert len(msg_chain) == 3


def test_merge():
    assert MessageChain(
        [Plain("Hello World!"), Plain("Hello World!"), Plain("How are you?")]
    ).merge() == MessageChain([Plain("Hello World!Hello World!How are you?")])
    assert MessageChain(
        [Plain("Hello World!"), Plain("Hello World!"), Plain("How are you?"), At(12345)]
    ).merge() == MessageChain([Plain("Hello World!Hello World!How are you?"), At(12345)])


def test_replace():
    assert MessageChain(
        [Plain("Hello World!"), Plain("Hello World!"), Plain("How are you?"), At(1), "yo"]
    ).replace(MessageChain(["Hello World!"]), MessageChain(["No!"])) == MessageChain(
        ["No!No!How are you?", At(1), "yo"]
    )
    assert MessageChain([Plain("Hello World!"), Plain("Hello World!"), Plain("How are you?"), At(1)]).replace(
        MessageChain(["Hello World!"]), MessageChain(["No!"])
    ) == MessageChain(["No!No!How are you?", At(1)])


def test_list_method():
    msg_chain = MessageChain([Plain("Hello World!"), Plain("How are you?"), At(12345)])

    # count
    assert msg_chain.count(Plain) == 2
    assert msg_chain.count(At) == 1
    assert msg_chain.count(Quote) == 0
    assert msg_chain.count(At(12345)) == 1
    assert msg_chain.count(At(124324)) == 0

    # index
    assert msg_chain.index(At) == 2
    assert msg_chain.index(Plain) == 0
    assert msg_chain.index(Quote) is None

    # extend
    assert msg_chain.extend(Plain("hi"), MessageChain(["good"]), ["why"], "obj", copy=True) == MessageChain(
        [
            Plain("Hello World!"),
            Plain("How are you?"),
            At(12345),
            Plain("hi"),
            Plain("good"),
            Plain("why"),
            Plain("obj"),
        ]
    )

    # append
    msg_chain.append("yo")
    msg_chain.append(At(1))
    assert BaseText("a") == Plain("a")
    assert msg_chain == MessageChain(
        [Plain("Hello World!"), Plain("How are you?"), At(12345), Plain("yo"), At(1)]
    )


if __name__ == "__main__":
    pytest.main([__file__, "-vvv"])
