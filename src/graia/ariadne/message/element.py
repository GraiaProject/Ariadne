"""Ariadne 中的消息元素"""
import abc
from base64 import b64decode, b64encode
from datetime import datetime
from enum import Enum
from json import dumps as j_dump
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, NoReturn, Optional, Union

from pydantic import validator
from pydantic.fields import Field

from ..context import upload_method_ctx
from ..exception import InvalidArgument
from ..model import AriadneBaseModel, Friend, Member, Stranger, UploadMethod
from ..util import wrap_bracket

if TYPE_CHECKING:
    from ..typing import ReprArgs
    from .chain import MessageChain


class NotSendableElement(Exception):
    """
    指示一个元素是不可发送的.
    """


class Element(AriadneBaseModel, abc.ABC):
    """
    指示一个消息中的元素.
    type (str): 元素类型
    """

    type: str
    """元素类型"""

    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))

    @staticmethod
    def asDisplay() -> str:
        """返回该元素的 "显示" 形式字符串, 趋近于你见到的样子.

        Returns:
            str: "显示" 字符串.
        """
        return ""

    def asPersistentString(self) -> str:
        """持久化字符串表示.

        Returns:
            str: 持久化字符串.
        """
        data: str = wrap_bracket(
            j_dump(
                self.dict(
                    exclude={"type"},
                ),
                indent=None,
                separators=(",", ":"),
            )
        )
        return f"[mirai:{self.type}:{data}]"

    def prepare(self) -> None:
        """
        为元素被发送进行准备,
        若无异常被引发, 则完成本方法后元素应可被发送.

        保留空实现以允许不需要 `prepare`的元素类型存在.

        若本元素设计时便不可被发送, 请引发 `NotSendableElement` 异常.
        """

    def __repr_args__(self) -> "ReprArgs":
        return list(self.dict(exclude={"type"}).items())

    def __str__(self) -> str:
        return self.asDisplay()

    def __add__(self, content: Union["MessageChain", List["Element"], "Element", str]) -> "MessageChain":
        from .chain import MessageChain

        if isinstance(content, str):
            content = Plain(content)
        if isinstance(content, Element):
            content = [content]
        if isinstance(content, MessageChain):
            content: List[Element] = content.__root__
        return MessageChain(content + [self], inline=True)

    def __radd__(self, content: Union["MessageChain", List["Element"], "Element", str]) -> "MessageChain":
        from .chain import MessageChain

        if isinstance(content, str):
            content = Plain(content)
        if isinstance(content, Element):
            content = [content]
        if isinstance(content, MessageChain):
            content: List[Element] = content.__root__
        return MessageChain([self] + content, inline=True)


class Plain(Element):
    """代表消息中的文本元素"""

    type: str = "Plain"

    text: str
    """实际的文本"""

    def __init__(self, text: str, **kwargs) -> None:
        """实例化一个 Plain 消息元素, 用于承载消息中的文字.

        Args:
            text (str): 元素所包含的文字
        """
        super().__init__(text=text, **kwargs)

    def asDisplay(self) -> str:
        return self.text

    def asPersistentString(self) -> str:
        return self.text


class Source(Element):
    """表示消息在一个特定聊天区域内的唯一标识"""

    type: str = "Source"

    id: int
    """消息 ID"""

    time: datetime
    """发送时间"""

    def prepare(self) -> NoReturn:
        raise NotSendableElement

    def asPersistentString(self) -> str:
        return ""

    async def fetchOriginal(self) -> "MessageChain":
        """尝试从本元素恢复原本的消息链, 有可能失败.

        Returns:
            MessageChain: 原来的消息链.
        """
        from ..context import ariadne_ctx

        ariadne = ariadne_ctx.get()

        return (await ariadne.getMessageFromId(self.id)).messageChain


class Quote(Element):
    """表示消息中回复其他消息/用户的部分, 通常包含一个完整的消息链(`origin` 属性)"""

    type: str = "Quote"

    id: int
    """引用的消息 ID"""

    groupId: int
    """引用消息所在群号 (好友消息为 0)"""

    senderId: int
    """发送者 QQ 号"""

    targetId: int
    """原消息的接收者QQ号 (或群号) """

    origin: "MessageChain"
    """原来的消息链"""

    @validator("origin", pre=True, allow_reuse=True)
    def _(cls, v):
        from .chain import MessageChain

        return MessageChain(v)  # no need to parse objects, they are universal!

    def prepare(self) -> NoReturn:
        raise NotSendableElement

    def asPersistentString(self) -> str:
        return ""


class At(Element):
    """该消息元素用于承载消息中用于提醒/呼唤特定用户的部分."""

    type: str = "At"

    target: int
    """At 的目标 QQ 号"""

    display: Optional[str] = None
    """显示名称"""

    def __init__(self, target: Union[int, Member] = ..., **data) -> None:
        """实例化一个 At 消息元素, 用于承载消息中用于提醒/呼唤特定用户的部分.

        Args:
            target (int): 需要提醒/呼唤的特定用户的 QQ 号(或者说 id.)
        """
        if target is not ...:
            if isinstance(target, int):
                data.update(target=target)
            else:
                data.update(target=target.id)
        super().__init__(**data)

    def __eq__(self, other: "At"):
        return isinstance(other, At) and self.target == other.target

    def prepare(self) -> None:
        try:
            if upload_method_ctx.get() != UploadMethod.Group:
                raise InvalidArgument(
                    f"you cannot use this element in this method: {upload_method_ctx.get().value}"
                )
        except LookupError:
            pass

    def asDisplay(self) -> str:
        return f"@{self.display}" if self.display else f"@{self.target}"


class AtAll(Element):
    """该消息元素用于群组中的管理员提醒群组中的所有成员"""

    type: str = "AtAll"

    def __init__(self, *_, **__) -> None:
        super().__init__()

    def asDisplay(self) -> str:
        return "@全体成员"

    def prepare(self) -> None:
        try:
            if upload_method_ctx.get() != UploadMethod.Group:
                raise InvalidArgument(
                    f"you cannot use this element in this method: {upload_method_ctx.get().value}"
                )
        except LookupError:
            pass


class Face(Element):
    """表示消息中所附带的表情, 这些表情大多都是聊天工具内置的."""

    type: str = "Face"

    faceId: Optional[int] = None
    """QQ 表情编号, 优先于 name"""

    name: Optional[str] = None
    """QQ 表情名称"""

    def __init__(self, id: int = ..., name: str = ..., **data) -> None:
        if id is not ...:
            data.update(id=id)
        if name is not ...:
            data.update(name=name)
        super().__init__(**data)

    def asDisplay(self) -> str:
        return f"[表情: {self.name if self.name else self.faceId}]"

    def __eq__(self, other) -> bool:
        return isinstance(other, Face) and (self.faceId == other.faceId or self.name == other.name)


class MarketFace(Element):
    """表示消息中的商城表情.

    注意: 本类型不支持用户发送
    """

    type: str = "MarketFace"

    faceId: Optional[int] = Field(None, alias="id")
    """QQ 表情编号"""

    name: Optional[str] = None
    """QQ 表情名称"""

    def asDisplay(self) -> str:
        return f"[商城表情: {self.name if self.name else self.faceId}]"

    def __eq__(self, other) -> bool:
        return isinstance(other, MarketFace) and (self.faceId == other.faceId or self.name == other.name)


class Xml(Element):
    """表示消息中的 XML 消息元素"""

    type = "Xml"

    xml: str
    """XML文本"""

    def __init__(self, xml: str, **_) -> None:
        super().__init__(xml=xml)

    def asDisplay(self) -> str:
        return "[XML消息]"


class Json(Element):
    """表示消息中的 JSON 消息元素"""

    type = "Json"

    Json: str = Field(..., alias="json")
    """XML文本"""

    def __init__(self, json: Union[dict, str], **kwargs) -> None:
        if isinstance(json, dict):
            json = j_dump(json)
        super().__init__(json=json, **kwargs)

    def dict(self, *args, **kwargs):
        return super().dict(*args, **({**kwargs, "by_alias": True}))

    def asDisplay(self) -> str:
        return "[JSON消息]"


class App(Element):
    """表示消息中自带的 App 消息元素"""

    type = "App"

    content: str
    """App 内容"""

    def __init__(self, content: str, **_) -> None:
        super().__init__(content=content)

    def asDisplay(self) -> str:
        return "[APP消息]"


class PokeMethods(str, Enum):
    """戳一戳可用方法"""

    ChuoYiChuo = "ChuoYiChuo"
    """戳一戳"""

    BiXin = "BiXin"
    """比心"""

    DianZan = "DianZan"
    """点赞"""

    XinSui = "XinSui"
    """心碎"""

    LiuLiuLiu = "LiuLiuLiu"
    """666"""

    FangDaZhao = "FangDaZhao"
    """放大招"""

    BaoBeiQiu = "BaoBeiQiu"
    """宝贝球"""

    Rose = "Rose"
    """玫瑰花"""

    ZhaoHuanShu = "ZhaoHuanShu"
    """召唤术"""

    RangNiPi = "RangNiPi"
    """让你皮"""

    JeiYin = "JeiYin"
    """结印"""

    ShouLei = "ShouLei"
    """手雷"""

    GouYin = "GouYin"
    """勾引"""

    ZhuaYiXia = "ZhuaYiXia"
    """抓一下"""

    SuiPing = "SuiPing"
    """碎屏"""

    QiaoMen = "QiaoMen"
    """敲门"""


class Poke(Element):
    """表示消息中戳一戳消息元素"""

    type = "Poke"

    name: PokeMethods
    """戳一戳使用的方法"""

    def __init__(self, name: PokeMethods, *_, **__) -> None:
        super().__init__(name=name)

    def asDisplay(self) -> str:
        return f"[戳一戳:{self.name}]"


class Dice(Element):
    """表示消息中骰子消息元素"""

    type = "Dice"

    value: int
    """骰子值"""

    def __init__(self, value: int, *_, **__) -> None:
        super().__init__(value=value)

    def asDisplay(self) -> str:
        return f"[骰子:{self.value}]"


class MusicShareKind(str, Enum):
    """音乐分享的来源。"""

    NeteaseCloudMusic = "NeteaseCloudMusic"
    """网易云音乐"""

    QQMusic = "QQMusic"
    """QQ音乐"""

    MiguMusic = "MiguMusic"
    """咪咕音乐"""

    KugouMusic = "KugouMusic"
    """酷狗音乐"""

    KuwoMusic = "KuwoMusic"
    """酷我音乐"""


class MusicShare(Element):
    """表示消息中音乐分享消息元素"""

    type = "MusicShare"
    kind: MusicShareKind
    """音乐分享的来源"""

    title: Optional[str]
    """音乐标题"""

    summary: Optional[str]
    """音乐摘要"""

    jumpUrl: Optional[str]
    """音乐跳转链接"""

    pictureUrl: Optional[str]
    """音乐图片链接"""

    musicUrl: Optional[str]
    """音乐链接"""

    brief: Optional[str]
    """音乐简介"""

    def __init__(
        self,
        kind: MusicShareKind,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        jumpUrl: Optional[str] = None,
        pictureUrl: Optional[str] = None,
        musicUrl: Optional[str] = None,
        brief: Optional[str] = None,
        *_,
        **__,
    ) -> None:
        super().__init__(
            kind=kind,
            title=title,
            summary=summary,
            jumpUrl=jumpUrl,
            pictureUrl=pictureUrl,
            musicUrl=musicUrl,
            brief=brief,
        )

    def asDisplay(self) -> str:
        return f"[音乐分享:{self.title}, {self.brief}]"


class ForwardNode(AriadneBaseModel):
    """表示合并转发中的一个节点"""

    senderId: int
    """发送者 QQ 号 (决定显示头像)"""

    time: datetime
    """发送时间"""

    senderName: str
    """发送者显示名字"""

    messageChain: Optional["MessageChain"]
    """发送的消息链"""

    messageId: Optional[int]
    """缓存的消息 ID"""

    def __init__(
        self,
        target: Union[int, Friend, Member, Stranger] = ...,
        time: datetime = ...,
        message: "MessageChain" = ...,
        name: str = ...,
        **data,
    ) -> None:
        if target is not ...:
            if isinstance(target, int):
                data.update(senderId=target)
            else:
                data.update(senderId=target.id)
                if isinstance(target, Member):
                    data.update(senderName=target.name)
                else:
                    data.update(senderName=target.nickname)
        if time is not ...:
            data.update(time=time)
        if name is not ...:
            data.update(senderName=name)
        if message is not ...:
            data.update(messageChain=message)
        super().__init__(**data)


class Forward(Element):
    """
    指示合并转发信息

    nodeList (List[ForwardNode]): 转发的消息节点
    """

    type = "Forward"

    nodeList: List[ForwardNode]
    """转发节点列表"""

    def __init__(self, *nodes: Union[Iterable[ForwardNode], ForwardNode], **data) -> None:
        if nodes:
            nodeList: List[ForwardNode] = []
            for i in nodes:
                if isinstance(i, ForwardNode):
                    nodeList.append(i)
                else:
                    nodeList.extend(i)
            data.update(nodeList=nodeList)
        super().__init__(**data)

    def asDisplay(self) -> str:
        return f"[合并转发:共{len(self.nodeList)}条]"

    def asPersistentString(self) -> str:
        return ""


class File(Element):
    """指示一个文件信息元素"""

    type = "File"

    id: str
    """文件 ID"""

    name: str
    """文件名"""

    size: int
    """文件大小"""

    def asDisplay(self) -> str:
        return f"[文件:{self.name}]"

    def asPersistentString(self) -> str:
        return ""

    def prepare(self) -> None:
        raise NotSendableElement


class MiraiCode(Element):
    """Mirai 码, 并不建议直接使用. Ariadne 也不会提供互转换接口."""

    type = "MiraiCode"

    code: str
    """Mirai Code"""


class ImageType(Enum):
    """Image 类型的枚举."""

    Friend = "Friend"
    """好友消息"""

    Group = "Group"
    """群组消息"""

    Temp = "Temp"
    """临时消息"""

    Unknown = "Unknown"
    """未知消息"""


image_upload_method_type_map = {
    UploadMethod.Friend: ImageType.Friend,
    UploadMethod.Group: ImageType.Group,
    UploadMethod.Temp: ImageType.Temp,
}


class MultimediaElement(Element):
    """指示多媒体消息元素."""

    id: Optional[str]
    """元素 ID"""

    url: Optional[str] = None
    """元素的下载 url"""

    base64: Optional[str] = None
    """元素的 base64"""

    def __init__(
        self,
        id: Optional[str] = None,
        url: Optional[str] = None,
        *,
        path: Optional[Union[Path, str]] = None,
        base64: Optional[str] = None,
        data_bytes: Optional[bytes] = None,
        **kwargs,
    ) -> None:
        data = {}

        for key, value in kwargs.items():
            if key.lower().endswith("id"):
                data["id"] = value

        if sum([bool(url), bool(path), bool(base64)]) > 1:
            raise ValueError("Too many binary initializers!")
        # Web initializer
        data["id"] = data["id"] if "id" in data else id
        data["url"] = url
        # Binary initializer
        if path:
            if isinstance(path, str):
                path = Path(path)
            if not path.exists():
                raise FileNotFoundError(f"{path} is not exist!")
            data["base64"] = b64encode(path.read_bytes())
        elif base64:
            data["base64"] = base64
        elif data_bytes:
            data["base64"] = b64encode(data_bytes)
        super().__init__(**data, **kwargs)

    async def get_bytes(self) -> bytes:
        """尝试获取消息元素的 bytes, 注意, 你无法获取并不包含 url 且不包含 base64 属性的本元素的 bytes.

        Raises:
            ValueError: 你尝试获取并不包含 url 属性的本元素的 bytes.

        Returns:
            bytes: 元素原始数据
        """
        from .. import get_running

        if self.base64:
            return b64decode(self.base64)
        if not self.url:
            raise ValueError("you should offer a url.")
        session = get_running().adapter.session
        if not session:
            raise RuntimeError("Unable to get session!")
        async with session.get(self.url) as response:
            response.raise_for_status()
            data = await response.read()
            self.base64 = b64encode(data).decode("ascii")
            return data

    def asNoBinaryPersistentString(self) -> str:
        """生成不附带二进制数据的持久化字符串

        Returns:
            str: 持久化字符串
        """
        data: str = wrap_bracket(
            j_dump(
                self.dict(
                    exclude={"type", "base64"},
                ),
                indent=None,
                separators=(",", ":"),
            )
        )
        return f"[mirai:{self.type}:{data}]"

    @property
    def uuid(self):
        """多媒体元素的 uuid, 即元素在 mirai 内部的标识"""
        if self.id:
            return self.id.split(".")[0].strip("/{}").lower()
        return ""

    def __eq__(self, other: "MultimediaElement"):
        if self.__class__ is not other.__class__:
            return False
        if self.uuid and self.uuid == other.uuid:
            return True
        if self.url and self.url == other.url:
            return True
        if self.base64 and self.base64 == other.base64:
            return True
        return False


class Image(MultimediaElement):
    """指示消息中的图片元素"""

    type = "Image"

    id: Optional[str] = Field(None, alias="imageId")

    def toFlashImage(self) -> "FlashImage":
        """将 Image 转换为 FlashImage

        Returns:
            FlashImage: 转换后的 FlashImage
        """
        return FlashImage.parse_obj({**self.dict(), "type": "FlashImage"})

    @classmethod
    def fromFlashImage(cls, flash: "FlashImage") -> "Image":
        """从 FlashImage 构造 Image

        Returns:
            Image: 构造出的 Image
        """
        return cls.parse_obj({**flash.dict(), "type": "Image"})

    def asDisplay(self) -> str:
        return "[图片]"


class FlashImage(Image):
    """指示消息中的闪照元素"""

    type = "FlashImage"

    def toImage(self) -> "Image":
        """将 FlashImage 转换为 Image

        Returns:
            Image: 转换后的 Image
        """
        return Image.parse_obj({**self.dict(), "type": "Image"})

    @classmethod
    def fromImage(cls, image: "Image") -> "FlashImage":
        """从 Image 构造 FlashImage

        Returns:
            FlashImage: 构造出的 FlashImage
        """
        return cls.parse_obj({**image.dict(), "type": "FlashImage"})

    def asDisplay(self) -> str:
        return "[闪照]"


class Voice(MultimediaElement):
    """指示消息中的语音元素"""

    type = "Voice"

    id: Optional[str] = Field(None, alias="voiceId")

    length: Optional[int]
    """语音长度"""

    def asDisplay(self) -> str:
        return "[语音]"


def _update_forward_refs():
    """
    Inner function.
    Update the forward references.
    """
    from ..model import BotMessage
    from .chain import MessageChain

    Quote.update_forward_refs(MessageChain=MessageChain)
    ForwardNode.update_forward_refs(MessageChain=MessageChain)
    BotMessage.update_forward_refs(MessageChain=MessageChain)
