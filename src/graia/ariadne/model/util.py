"""用于 Ariadne 数据模型的工具类."""
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Union
from typing_extensions import NotRequired, TypedDict

from pydantic import BaseConfig, BaseModel, Extra

from ..util import snake_to_camel

if TYPE_CHECKING:
    from ..typing import AbstractSetIntStr, DictStrAny, MappingIntStrAny


class AriadneBaseModel(BaseModel):
    """Ariadne 一切数据模型的基类."""

    def __init__(self, **data: Any) -> None:
        """初始化模型. 直接向 pydantic 转发."""
        super().__init__(**data)

    def dict(
        self,
        *,
        include: Union[None, "AbstractSetIntStr", "MappingIntStrAny"] = None,
        exclude: Union[None, "AbstractSetIntStr", "MappingIntStrAny"] = None,
        by_alias: bool = False,
        skip_defaults: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        to_camel: bool = False,
    ) -> "DictStrAny":
        """转化为字典, 直接向 pydantic 转发."""
        _, *_ = by_alias, exclude_none, skip_defaults
        data = super().dict(
            include=include,  # type: ignore
            exclude=exclude,  # type: ignore
            by_alias=True,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=True,
        )
        if to_camel:
            data = {snake_to_camel(k): v for k, v in data.items()}
        return data

    class Config(BaseConfig):
        """Ariadne BaseModel 设置"""

        extra = Extra.allow
        arbitrary_types_allowed = True
        copy_on_model_validation = "none"
        json_encoders = {
            datetime: lambda dt: int(dt.timestamp()),
        }


class AriadneOptions(TypedDict):
    """Ariadne 内部的选项存储"""

    installed_log: NotRequired[Literal[True]]
    inject_bypass_listener: NotRequired[Literal[True]]
    default_account: NotRequired[int]
