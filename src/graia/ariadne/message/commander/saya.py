from dataclasses import dataclass, field
from typing import Callable, Dict, List, Union

from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.saya.behaviour import Behaviour
from graia.saya.cube import Cube
from graia.saya.schema import BaseSchema

from . import Arg, Commander, Slot


@dataclass
class CommandSchema(BaseSchema):
    """命令监听 Schema, 相当于 commander.command"""

    command: str
    settings: Dict[str, Union[Slot, Arg]] = field(default_factory=dict)
    dispatchers: List[BaseDispatcher] = field(default_factory=list)
    decorators: List[Decorator] = field(default_factory=list)

    def register(self, func: Callable, commander: Commander):
        """注册 func 至 commander

        Args:
            func (Callable): 命令函数
            commander (Commander): 命令对象
        """
        commander.command(self.command, self.settings, self.dispatchers, self.decorators)(func)


class CommanderBehaviour(Behaviour):
    """命令行为"""

    def __init__(self, commander: Commander) -> None:
        self.commander = commander

    def allocate(self, cube: Cube[CommandSchema]):
        if not isinstance(cube.metaclass, CommandSchema):
            return
        cube.metaclass.register(cube.content, self.commander)
        return True

    def uninstall(self, cube: Cube[CommandSchema]):
        if not isinstance(cube.metaclass, CommandSchema):
            return
        for val in self.commander.command_handlers[:]:
            if cube.content is val.callable:
                self.commander.command_handlers.remove(val)
        return True
