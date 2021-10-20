import abc
import sys
from base64 import b64encode
from datetime import datetime
from enum import Enum
from json import dumps as j_dump
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

from pydantic import BaseModel, validator
from pydantic.fields import Field

from graia.ariadne.context import adapter_ctx, application_ctx, upload_method_ctx
from graia.ariadne.exception import InvalidArgument
from graia.ariadne.model import AriadneBaseModel, UploadMethod, datetime_encoder

if TYPE_CHECKING:
    from graia.ariadne.message.chain import MessageChain


class Element(AriadneBaseModel, abc.ABC):
    """
    指示一个消息中的元素。
    type (str): 元素类型
    """

    type: str

    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))

    def asDisplay(self) -> str:
        return ""

    def prepare(self) -> None:
        """
        为元素被发送进行准备
        若无异常被引发，则完成本方法后元素应可被发送。
        保留空实现以允许不需要 `prepare`的元素类型存在。
        """


class Plain(Element):
    type: str = "Plain"
    text: str

    def __init__(self, text: str, **kwargs) -> None:
        """实例化一个 Plain 消息元素, 用于承载消息中的文字.

        Args:
            text (str): 元素所包含的文字
        """
        super().__init__(text=text, **kwargs)

    def asDisplay(self) -> str:
        return self.text


class Source(Element):
    "表示消息在一个特定聊天区域内的唯一标识"
    type: str = "Source"
    id: int
    time: datetime

    class Config:
        json_encoders = {
            datetime: datetime_encoder,
        }


class Quote(Element):
    "表示消息中回复其他消息/用户的部分, 通常包含一个完整的消息链(`origin` 属性)"
    type: str = "Quote"
    id: int
    groupId: int
    senderId: int
    targetId: int
    origin: "MessageChain"

    @validator("origin", pre=True, allow_reuse=True)
    def _(cls, v):
        from .chain import MessageChain

        return MessageChain(v)  # no need to parse objects, they are universal!


class At(Element):
    """该消息元素用于承载消息中用于提醒/呼唤特定用户的部分."""

    type: str = "At"
    target: int
    display: Optional[str] = None

    def __init__(self, target: int, **kwargs) -> None:
        """实例化一个 At 消息元素, 用于承载消息中用于提醒/呼唤特定用户的部分.

        Args:
            target (int): 需要提醒/呼唤的特定用户的 QQ 号(或者说 id.)
        """
        super().__init__(target=target, **kwargs)

    def prepare(self) -> None:
        try:
            if upload_method_ctx.get() != UploadMethod.Group:
                raise InvalidArgument(
                    "you cannot use this element in this method: {0}".format(
                        upload_method_ctx.get().value
                    )
                )
        except LookupError:
            pass

    def asDisplay(self) -> str:
        return f"[At:{self.display}({self.target})]"


class AtAll(Element):
    "该消息元素用于群组中的管理员提醒群组中的所有成员"
    type: str = "AtAll"

    def asDisplay(self) -> str:
        return "[AtAll]"

    def prepare(self) -> None:
        try:
            if upload_method_ctx.get() != UploadMethod.Group:
                raise InvalidArgument(
                    "you cannot use this element in this method: {0}".format(
                        upload_method_ctx.get().value
                    )
                )
        except LookupError:
            pass


class Face(Element):
    "表示消息中所附带的表情, 这些表情大多都是聊天工具内置的."
    type: str = "Face"
    faceId: int
    name: Optional[str] = None

    def asDisplay(self) -> str:
        return f"[表情:{self.faceId}]"


class Xml(Element):
    "表示消息中的 XML 消息元素"
    type = "Xml"
    xml: str

    def asDisplay(self) -> str:
        return "[XML消息]"


class Json(Element):
    "表示消息中的 JSON 消息元素"
    type = "Json"
    Json: str = Field(..., alias="json")

    def __init__(self, json: Union[dict, str], **kwargs) -> None:
        if isinstance(json, dict):
            json = j_dump(json)
        super().__init__(json=json, **kwargs)

    def dict(self, *args, **kwargs):
        return super().dict(*args, **({**kwargs, "by_alias": True}))

    def asDisplay(self) -> str:
        return "[JSON消息]"


class App(Element):
    "表示消息中自带的 App 消息元素"
    type = "App"
    content: str

    def asDisplay(self) -> str:
        return "[APP消息]"


class PokeMethods(Enum):
    "戳一戳可用方法"
    ChuoYiChuo = "ChuoYiChuo"
    BiXin = "BiXin"
    DianZan = "DianZan"
    XinSui = "XinSui"
    LiuLiuLiu = "LiuLiuLiu"
    FangDaZhao = "FangDaZhao"
    BaoBeiQiu = "BaoBeiQiu"
    Rose = "Rose"
    ZhaoHuanShu = "ZhaoHuanShu"
    RangNiPi = "RangNiPi"
    JeiYin = "JeiYin"
    ShouLei = "ShouLei"
    GouYin = "GouYin"
    ZhuaYiXia = "ZhuaYiXia"
    SuiPing = "SuiPing"
    QiaoMen = "QiaoMen"


class Poke(Element):
    "表示消息中戳一戳消息元素"
    type = "Poke"
    name: PokeMethods

    def asDisplay(self) -> str:
        return f"[戳一戳:{self.name}]"


class Dice(Element):
    "表示消息中骰子消息元素"
    type = "Dice"
    value: int

    def asDisplay(self) -> str:
        return f"[骰子:{self.value}]"


class MusicShare(Element):
    "表示消息中音乐分享消息元素"
    type = "MusicShare"
    kind: Optional[str]
    title: Optional[str]
    summary: Optional[str]
    jumpUrl: Optional[str]
    pictureUrl: Optional[str]
    musicUrl: Optional[str]
    brief: Optional[str]

    def asDisplay(self) -> str:
        return f"[音乐分享:{self.title}]"


class ForwardNode(BaseModel):
    "表示合并转发中的一个节点"
    senderId: int
    time: datetime
    senderName: str
    messageChain: Optional["MessageChain"]
    messageId: Optional[int]

    class Config:
        json_encoders = {
            datetime: datetime_encoder,
        }


class Forward(Element):
    """
    指示合并转发信息

    nodeList (List[ForwardNode]): 转发的消息节点
    """

    type = "Forward"
    nodeList: List[ForwardNode]

    def asDisplay(self) -> str:
        return f"[合并转发:共{len(self.nodeList)}条]"


class File(Element):
    "指示一个文件信息元素"
    type = "File"
    id: str
    name: str
    size: int

    def asDisplay(self) -> str:
        return f"[文件:{self.name}]"


class ImageType(Enum):
    Friend = "Friend"
    Group = "Group"
    Temp = "Temp"
    Unknown = "Unknown"


image_upload_method_type_map = {
    UploadMethod.Friend: ImageType.Friend,
    UploadMethod.Group: ImageType.Group,
    UploadMethod.Temp: ImageType.Temp,
}


class Image(Element):
    "指示消息中的图片元素"
    type = "Image"
    ready: bool = True
    imageId: Optional[str] = None
    url: Optional[str] = None
    path: Optional[Path] = None
    base64: Optional[str] = None
    data_bytes: Optional[bytes] = None

    def __init__(
        self,
        imageId: Optional[str] = None,
        url: Optional[str] = None,
        path: Optional[Path] = None,
        base64: Optional[str] = None,
        *,
        data_bytes: Optional[bytes] = None,
        flash: Optional["FlashImage"] = None,
        **kwargs,
    ) -> None:
        if flash:
            super().__init__(**flash.dict() | {"type": "Image"})
            return
        data = {}
        data["imageId"] = imageId
        data["url"] = url
        data["path"] = path
        if data_bytes and base64:
            raise ValueError("Can't present base64 and bytes data at the same time!")
        if base64:
            data["base64"] = base64
        if data_bytes:
            data["base64"] = b64encode(data_bytes)
        super().__init__(**data, **kwargs)

    def asDisplay(self) -> str:
        return "[图片]"

    async def get_bytes(self, url: str = None) -> bytes:
        """从远端服务器获取消息元素的 bytes, 注意, 你无法获取并不包含 url 属性的本元素的 bytes.

        Args:
            url (str, optional): 如果提供, 则从本参数获取 bytes. 默认为 None.

        Raises:
            ValueError: 你尝试获取并不包含 url 属性的本元素的 bytes.

        Returns:
            bytes: 元素原始数据
        """
        if not (self.url or url):
            raise ValueError("you should offer a url.")
        session = adapter_ctx.get().session
        async with session.get(self.url or url) as response:
            response.raise_for_status()
            return await response.read()


class FlashImage(Image):
    "指示消息中的闪照元素"
    type = "FlashImage"

    def __init__(
        self,
        imageId: Optional[str] = None,
        url: Optional[str] = None,
        path: Optional[Path] = None,
        base64: Optional[str] = None,
        *,
        data_bytes: Optional[bytes] = None,
        normal: Optional["Image"] = None,
        **kwargs,
    ) -> None:
        if normal:
            super().__init__(**normal.dict() | {"type": "FlashImage"})
        data = {}
        data["type"] = type
        data["imageId"] = imageId
        data["url"] = url
        data["path"] = path
        if data_bytes and base64:
            raise ValueError("Can't present base64 and bytes data at the same time!")
        if base64:
            data["base64"] = base64
        if data_bytes:
            data["base64"] = b64encode(data_bytes)
        super().__init__(**data, **kwargs)

    def asDisplay(self):
        return "[闪照]"


class Voice(Element):
    "指示消息中的语音元素"
    type = "Voice"
    voiceId: Optional[str]
    url: Optional[str]
    path: Optional[Path]
    base64: Optional[str]
    length: Optional[int]
    data_bytes: Optional[bytes]

    def __init__(
        self,
        voiceId: Optional[str] = None,
        url: Optional[str] = None,
        path: Optional[Path] = None,
        base64: Optional[str] = None,
        *,
        data_bytes: Optional[bytes] = None,
        **kwargs,
    ) -> None:
        data = {}
        data["type"] = type
        data["voiceId"] = voiceId
        data["url"] = url
        data["path"] = path
        if data_bytes and base64:
            raise ValueError("Can't present base64 and bytes data at the same time!")
        if base64:
            data["base64"] = base64
        if data_bytes:
            data["base64"] = b64encode(data_bytes)
        super().__init__(**data, **kwargs)

    def asDisplay(self) -> str:
        return "[语音]"

    async def get_bytes(self, url: str = None) -> bytes:
        """从远端服务器获取消息元素的 bytes, 注意, 你无法获取并不包含 url 属性的本元素的 bytes.

        Args:
            url (str, optional): 如果提供, 则从本参数获取 bytes. 默认为 None.

        Raises:
            ValueError: 你尝试获取并不包含 url 属性的本元素的 bytes.

        Returns:
            bytes: 元素原始数据
        """
        if not (self.url or url):
            raise ValueError("you should offer a url.")
        session = adapter_ctx.get().session
        async with session.get(self.url or url) as response:
            response.raise_for_status()
            return await response.read()


def _update_forward_refs():
    """
    Inner function.
    Update the forward references.
    """
    from .chain import MessageChain

    Quote.update_forward_refs(MessageChain=MessageChain)
    ForwardNode.update_forward_refs(MessageChain=MessageChain)
