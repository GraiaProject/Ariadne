"""Ariadne 消息相关的导入集合"""

# no error

from ..message.chain import MessageChain as MessageChain
from ..message.commander import Arg as Arg, Commander as Commander, Slot as Slot
from ..message.component import Component as Component
from ..message.element import (
    App as App,
    At as At,
    AtAll as AtAll,
    Dice as Dice,
    Element as Element,
    Face as Face,
    File as File,
    FlashImage as FlashImage,
    Forward as Forward,
    ForwardNode as ForwardNode,
    Image as Image,
    ImageType as ImageType,
    MultimediaElement as MultimediaElement,
    MusicShare as MusicShare,
    NotSendableElement as NotSendableElement,
    Plain as Plain,
    Poke as Poke,
    PokeMethods as PokeMethods,
    Quote as Quote,
    Source as Source,
    Voice as Voice,
)
from ..message.formatter import Formatter as Formatter
from ..message.parser.base import DetectPrefix as DetectPrefix, DetectSuffix as DetectSuffix
from ..message.parser.literature import (
    BoxParameter as BoxParameter,
    Literature as Literature,
    ParamPattern as ParamPattern,
    SwitchParameter as SwitchParameter,
)
from ..message.parser.twilight import (
    FORCE as FORCE,
    NOSPACE as NOSPACE,
    PRESERVE as PRESERVE,
    ArgumentMatch as ArgumentMatch,
    ElementMatch as ElementMatch,
    FullMatch as FullMatch,
    Match as Match,
    RegexMatch as RegexMatch,
    Sparkle as Sparkle,
    Twilight as Twilight,
    UnionMatch as UnionMatch,
    WildcardMatch as WildcardMatch,
)
from ..util.send import Bypass as Bypass, Ignore as Ignore, Safe as Safe, Strict as Strict
