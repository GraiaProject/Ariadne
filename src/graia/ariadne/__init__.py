"""Ariadne

一个优雅的 QQ Bot 框架.
"""

from importlib.metadata import Distribution

from .app import Ariadne as Ariadne  # noqa: F401

if next(iter(Distribution.discover(name="graia-application-mirai")), None) is not None:
    raise ImportError("`graia-application-mirai` is out of support.")
