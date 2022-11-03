import warnings

from ..chain import MessageChain as BaseMessageChain

MessageChain = BaseMessageChain

warnings.warn(
    "graia.ariadne.message.exp.MessageChain is no longer needed, and will be removed in Ariadne 1.0."
)
