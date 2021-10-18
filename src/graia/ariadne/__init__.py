from typing import TYPE_CHECKING

if not TYPE_CHECKING:  # for init event and message
    import graia.ariadne.event.lifecycle
    import graia.ariadne.event.message
    import graia.ariadne.event.mirai
    import graia.ariadne.event.network
    import graia.ariadne.message.chain
    import graia.ariadne.message.element
