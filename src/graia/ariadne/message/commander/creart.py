from __future__ import annotations

from typing import TYPE_CHECKING

from creart import CreateTargetInfo, create, exists_module
from creart.creator import AbstractCreator

from . import Commander

if TYPE_CHECKING:
    from .saya import CommanderBehaviour


class CommanderCreator(AbstractCreator):
    targets = (
        CreateTargetInfo(
            "graia.ariadne.message.commander",
            "Commander",
            humanized_name="Commander",
            description="<common,graia,ariadne,commander,parser> Fast and typing-based message parser.",
            author=["GraiaProject@github"],
        ),
    )

    @staticmethod
    def create(create_type: type[Commander]) -> Commander:
        from graia.broadcast import Broadcast

        commander = create_type(create(Broadcast))
        if exists_module("graia.saya"):
            from graia.saya import Saya

            from .saya import CommanderBehaviour

            create(Saya).install_behaviours(CommanderBehaviour(commander))
        return commander


class CommanderBehaviourCreator(AbstractCreator):
    targets = (CreateTargetInfo("graia.ariadne.message.commander.saya", "CommanderBehaviour"),)

    @staticmethod
    def available() -> bool:
        return exists_module("graia.saya")

    @staticmethod
    def create(create_type: type[CommanderBehaviour]) -> CommanderBehaviour:
        return create_type(create(Commander))
