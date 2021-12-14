import pytest

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, AtAll, Element, Plain, Quote, Source


def test_create():
    chain = MessageChain([Plain("Hello World"), At(12345), Plain("1234567")])
    assert (
        MessageChain.create("Hello World", [At(12345)], MessageChain([Plain("1234567")])).__root__
        == chain.__root__
    )
    assert MessageChain.parse_obj(
        [{"type": "At", "target": 12345}, {"type": "Plain", "text": "hello"}, {"type": "Broken"}, 5]
    ) == MessageChain([At(12345), "hello"])


def test_subchain():
    # group 1
    assert MessageChain.create("hello world").subchain(slice((0, 3), None)) == MessageChain(
        [Plain(text="lo world")]
    )
    assert MessageChain.create("hello world").subchain(slice(None, (1, 7))) == MessageChain(
        [Plain(text="hello w")]
    )
    assert MessageChain.create("hello world").subchain(slice((0, 3), (1, 7))) == MessageChain(
        [Plain(text="lo w")]
    )

    # group 2
    assert MessageChain.create("hello", At(12345), "world").subchain(slice((0, 3), (3, 2))) == MessageChain(
        [Plain(text="lo"), At(12345), Plain("wo")]
    )
    assert MessageChain.create("hello", At(12345), "world").subchain(slice((0, 3), None)) == MessageChain(
        [Plain(text="lo"), At(12345), Plain("world")]
    )
    assert MessageChain.create("hello", At(12345), "world").subchain(slice(None, (3, 2))) == MessageChain(
        [Plain(text="hello"), At(12345), Plain("wo")]
    )

    # group 3
    assert MessageChain.create("hello", At(12345)).subchain(
        slice((0, 3), (2, 2)), ignore_text_index=True
    ) == MessageChain([Plain(text="lo"), At(12345)])
    assert MessageChain.create(["hello"]).subchain(slice((1,), (1,))) == MessageChain([])
    with pytest.raises(ValueError):
        assert MessageChain.create("hello", At(12345)).subchain(slice((0, 3), (2, 2))) == MessageChain(
            [Plain(text="lo"), At(12345)]
        )
    with pytest.raises(ValueError):
        MessageChain.create("hello", At(12345)).subchain(slice((0, 3), (2, 2)))

    assert MessageChain.create(At(12345)).subchain(
        slice((0, 1), None), ignore_text_index=True
    ) == MessageChain([At(12345)])
    with pytest.raises(ValueError):
        MessageChain.create(At(12345)).subchain(slice((0, 1), None))

    assert MessageChain.create(At(12345), "hello").subchain(
        slice((0, 3), None), ignore_text_index=True
    ) == MessageChain([At(12345), "hello"])
    with pytest.raises(ValueError):
        MessageChain.create(At(12345), "hello").subchain(slice((0, 3), None))


def test_include_exclude():
    msg_chain = MessageChain.create("Hello", At(target=12345))
    assert msg_chain.include(Plain) == MessageChain([Plain(text="Hello")])
    assert msg_chain.exclude(Plain) == MessageChain([At(target=12345)])


def test_split():
    msg_chain = MessageChain.create("Hello world!", At(target=12345))
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
    msg_chain = MessageChain.create("Hello world!", At(target=12345))
    assert msg_chain.removeprefix("Hello") == MessageChain([Plain(text=" world!"), At(target=12345)])
    assert msg_chain.removesuffix("world!") == MessageChain([Plain(text="Hello world!"), At(target=12345)])
    assert MessageChain(["hello world"]).removesuffix("world") == MessageChain([Plain("hello ")])
    assert not msg_chain.endswith("world!")
    assert not msg_chain.startswith("world!")
    assert msg_chain.startswith("Hello")

    assert MessageChain(["hello world"]).endswith("world")

    assert not MessageChain([At(12345), "hello"]).startswith("hello")


def test_mapping_string():
    msg_chain = MessageChain.create("Hello world!", At(target=12345))
    assert msg_chain.asMappingString() == ("Hello world!\x021_At\x03", {1: At(target=12345)})
    string, mapping = msg_chain.asMappingString()
    new_string = string.removeprefix("Hello world")  # new_string = "!\x021_At\x03"
    assert MessageChain.fromMappingString(new_string, mapping) == MessageChain(
        [Plain(text="!"), At(target=12345)]
    )
    with pytest.raises(ValueError):
        MessageChain.fromMappingString("\x020_At\x03", {0: AtAll()})

    assert MessageChain.create(At(12345), "  hello!").asMappingString()[0] == "\x020_At\x03  hello!"

    assert (
        MessageChain.create(At(12345), "  hello!").asMappingString(remove_extra_space=True)[0]
        == "\x020_At\x03 hello!"
    )

    assert (
        MessageChain.create(
            Source(id=1, time=12433531),
            Quote(id=41342, groupId=1234, senderId=123421, targetId=123422, origin=MessageChain("Hello")),
            "  hello!",
        ).asMappingString()[0]
        == "  hello!"
    )

    assert (
        MessageChain.create(
            Source(id=1, time=12433531),
            Quote(id=41342, groupId=1234, senderId=123421, targetId=123422, origin=MessageChain("Hello")),
            "  hello!",
        ).asMappingString(remove_extra_space=True)[0]
        == " hello!"
    )


def test_has():
    msg_chain = MessageChain.create("Hello", At(target=12345))
    assert msg_chain.has(MessageChain([Plain(text="Hello")]))
    assert not msg_chain.has(MessageChain([Plain(text="LOL")]))
    assert msg_chain.has(At(target=12345))
    assert not msg_chain.has(At(target=12152))
    assert msg_chain.has("Hello")
    assert msg_chain.has(msg_chain)
    assert msg_chain.has(Plain)
    assert not msg_chain.has(Quote)
    assert msg_chain.findSubChain(MessageChain(["Hello"])) == [0]
    assert msg_chain.findSubChain(MessageChain(["Hello system"])) == []
    assert msg_chain.findSubChain(MessageChain(["HeHeHe"])) == []
    assert MessageChain(["HeHe"]).findSubChain(MessageChain(["HeHeHe"])) == []
    assert MessageChain(["HeHeHeHe"]).findSubChain(MessageChain(["HeHeHe"])) == [0, 2]
    assert MessageChain(["HeHeHaHaHoHo"]).findSubChain(MessageChain(["HeHeHoHo"])) == []


def test_contain():
    msg_chain = MessageChain.create("Hello", At(target=12345))
    assert MessageChain([Plain(text="Hello")]) in msg_chain
    assert At(target=12345) in msg_chain
    assert At(target=12152) not in msg_chain
    assert msg_chain.has("Hello")
    assert msg_chain in msg_chain


def test_get():
    msg_chain = MessageChain.create("Hello World!", At(target=12345), "Foo test!")
    assert msg_chain[Plain] == [Plain("Hello World!"), Plain("Foo test!")]
    assert msg_chain[Plain, 1] == [Plain("Hello World!")]
    assert msg_chain[1] == At(target=12345)
    assert msg_chain[(0,):(2,)] == MessageChain(["Hello World!", At(target=12345)])
    assert msg_chain[(0, 2):(2,)] == MessageChain(["llo World!", At(target=12345)])
    with pytest.raises(NotImplementedError):
        msg_chain["trial"]
    assert msg_chain.get(Plain) == msg_chain[Plain]
    assert msg_chain.get(Plain, 1) == msg_chain[Plain, 1]
    assert msg_chain.getOne(Plain, 0) == Plain("Hello World!")
    assert msg_chain.getOne(Plain, 1) == Plain("Foo test!")
    assert msg_chain.getFirst(Plain) == Plain("Hello World!")


def test_onlycontains():
    msg_chain = MessageChain.create("Hello World!", At(target=12345), "Foo test!")
    assert msg_chain.onlyContains(Plain, At)


def test_prepare():
    msg_chain = MessageChain.create(
        Source(id=1, time=12433531),
        Quote(id=41342, groupId=1234, senderId=123421, targetId=123422, origin=MessageChain("Hello")),
        "  hello!",
    )
    assert not msg_chain.onlyContains(Plain)
    assert msg_chain.asSendable().__root__ != msg_chain.__root__
    assert msg_chain.prepare(copy=True).__root__ != msg_chain.__root__
    msg_chain.prepare()
    assert msg_chain.onlyContains(Plain)
    assert msg_chain.asSendable().__root__ == msg_chain.__root__


def test_persistent():
    msg_chain = MessageChain.create(
        Source(id=1, time=12433531),
        Quote(id=41342, groupId=1234, senderId=123421, targetId=123422, origin=MessageChain("Hello")),
        "hello!",
    )
    assert msg_chain.asPersistentString() == "hello!"
    assert MessageChain.fromPersistentString('hello![_[mirai:At:{"target":12345}]') == MessageChain(
        ["hello![", At(12345)]
    )


def test_presentation():
    msg_chain = MessageChain.create("Hello World!", At(target=12345), "Foo test!")
    assert msg_chain.asDisplay() == "Hello World!@12345Foo test!"
    assert str(msg_chain) == msg_chain.asDisplay()
    print(repr(msg_chain))
    assert (
        repr(msg_chain)
        == "MessageChain([Plain(text='Hello World!'), At(target=12345), Plain(text='Foo test!')])"
    )
    assert eval(repr(msg_chain)) == msg_chain


def test_magic():
    msg_chain = MessageChain.create("Hello world!", At(target=12345))
    for e in msg_chain:
        assert isinstance(e, Element)

    assert MessageChain(["Hello"]) == ["Hello"]
    assert MessageChain(["hello"]) == MessageChain.create("hello")

    assert MessageChain(["Hello World!"]) + MessageChain(["Goodbye World!"]) == MessageChain(
        [Plain("Hello World!"), Plain("Goodbye World!")]
    )
    assert MessageChain(["Hello World!"]) + [Plain("Goodbye World!")] == MessageChain(
        [Plain("Hello World!"), Plain("Goodbye World!")]
    )
    assert MessageChain(["Hello World!"]) * 2 == MessageChain([Plain("Hello World!"), Plain("Hello World!")])

    msg_chain = MessageChain.create("Hello World!")
    msg_chain *= 2
    assert msg_chain == MessageChain([Plain("Hello World!"), Plain("Hello World!")])
    msg_chain += [Plain("How are you?")]
    assert msg_chain == MessageChain([Plain("Hello World!"), Plain("Hello World!"), Plain("How are you?")])
    assert len(msg_chain) == 3

    msg_chain = MessageChain.create("Hello World!")
    msg_chain *= 2
    assert msg_chain == MessageChain([Plain("Hello World!"), Plain("Hello World!")])
    msg_chain += MessageChain([Plain("How are you?")])
    assert msg_chain == MessageChain([Plain("Hello World!"), Plain("Hello World!"), Plain("How are you?")])
    assert len(msg_chain) == 3


def test_merge():
    assert MessageChain([Plain("Hello World!"), Plain("Hello World!"), Plain("How are you?")]).merge(
        copy=True
    ) == MessageChain([Plain("Hello World!Hello World!How are you?")])
    assert MessageChain(
        [Plain("Hello World!"), Plain("Hello World!"), Plain("How are you?"), At(12345)]
    ).merge(copy=True) == MessageChain([Plain("Hello World!Hello World!How are you?"), At(12345)])


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
    assert msg_chain == MessageChain(
        [Plain("Hello World!"), Plain("How are you?"), At(12345), Plain("yo"), At(1)]
    )


if __name__ == "__main__":
    pytest.main([__file__, "-vvv"])
