from graia.broadcast import Dispatchable
from pydantic import BaseModel, validator

from ..dispatcher import ApplicationDispatcher
from ..exception import InvalidEventTypeDefinition


class MiraiEvent(Dispatchable, BaseModel):
    type: str

    @validator("type", allow_reuse=True)
    def type_limit(cls, v):
        if cls.type != v:
            raise InvalidEventTypeDefinition(
                "{0}'s type must be '{1}', not '{2}'".format(cls.__name__, cls.type, v)
            )
        return v

    class Config:
        extra = "ignore"

    Dispatcher = ApplicationDispatcher
