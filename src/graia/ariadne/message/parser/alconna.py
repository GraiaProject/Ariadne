"""
该文件仅作为兼容用
"""

from arclet.alconna.graia import Alconna as _Alc
from arclet.alconna.graia import AlconnaDispatcher as _Alc_Disp
from arclet.alconna.graia import AlconnaHelpMessage as _Alc_Hlp
from loguru import logger

logger.warning(
    DeprecationWarning(
        "This module is deprecatedand will be removed in 0.7.0, use arclet.alconna.graia instead"
    )
)

Alconna = _Alc
AlconnaDispatcher = _Alc_Disp
AlconnaHelpMessage = _Alc_Hlp
