from dataclasses import dataclass, field
from typing import Callable, List

from graia.broadcast.entities.decorator import Decorator
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.saya.behaviour import Behaviour
from graia.saya.cube import Cube
from graia.saya.schema import BaseSchema

from . import Console


@dataclass
class ConsoleSchema(BaseSchema):
    dispatchers: List[BaseDispatcher] = field(default_factory=list)
    decorators: List[Decorator] = field(default_factory=list)

    def register(self, func: Callable, console: Console):
        console.register(self.dispatchers, self.decorators)(func)


class ConsoleBehaviour(Behaviour):
    def __init__(self, console: Console) -> None:
        self.console = console

    def allocate(self, cube: Cube[ConsoleSchema]):
        if not isinstance(cube.metaclass, ConsoleSchema):
            return
        cube.metaclass.register(cube.content, self.console)
        return True

    def uninstall(self, cube: Cube[ConsoleSchema]):
        if not isinstance(cube.metaclass, ConsoleSchema):
            return
        for val in self.console.registry[:]:
            if cube.content is val[0]:
                self.console.registry.remove(val)
        return True
