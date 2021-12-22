"""Ariadne
一个优雅的 QQ Bot 框架.
"""
import graia.ariadne.event.lifecycle  # noqa: F401
import graia.ariadne.event.message  # noqa: F401
import graia.ariadne.event.mirai  # noqa: F401
import graia.ariadne.event.network  # noqa: F401

# init event

ARIADNE_ASCII_LOGO = "\n".join(
    (
        r"                _           _             ",
        r"     /\        (_)         | |            ",
        r"    /  \   _ __ _  __ _  __| |_ __   ___  ",
        r"   / /\ \ | '__| |/ _` |/ _` | '_ \ / _ \ ",
        r"  / ____ \| |  | | (_| | (_| | | | |  __/ ",
        r" /_/    \_\_|  |_|\__,_|\__,_|_| |_|\___| ",
        r"",
    )
)
