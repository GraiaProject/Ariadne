"""本模块提供 Ariadne 消息相关部件."""
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import Field, validator

from ..model.util import AriadneBaseModel
from ..util import internal_cls

if TYPE_CHECKING:
    from .chain import MessageChain


@internal_cls()
class Source(AriadneBaseModel):
    """表示消息在一个特定聊天区域内的唯一标识"""

    type = "Source"

    id: int
    """消息 ID"""

    time: datetime
    """发送时间"""

    def __int__(self):
        return self.id

    async def fetch_original(self) -> "MessageChain":
        """尝试从本标记恢复原本的消息链, 有可能失败.

        Returns:
            MessageChain: 原来的消息链.
        """
        from ..app import Ariadne

        return (await Ariadne.current().get_message_from_id(self.id)).message_chain


@internal_cls()
class Quote(AriadneBaseModel):
    """表示消息中回复其他消息/用户的部分, 通常包含一个完整的消息链(`origin` 属性)"""

    type = "Quote"

    id: int
    """引用的消息 ID"""

    group_id: int = Field(..., alias="groupId")
    """引用消息所在群号 (好友消息为 0)"""

    sender_id: int = Field(..., alias="senderId")
    """发送者 QQ 号"""

    target_id: int = Field(..., alias="targetId")
    """原消息的接收者QQ号 (或群号) """

    origin: "MessageChain"
    """原来的消息链"""

    @validator("origin", pre=True, allow_reuse=True)
    def _(cls, v):
        from .chain import MessageChain

        return MessageChain(v)  # no need to parse objects, they are universal!

    def as_persistent_string(self) -> str:
        return ""
