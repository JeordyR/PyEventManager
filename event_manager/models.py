__all__ = ["EventModel"]

from typing import ClassVar, LiteralString, TypeVar

from pydantic import BaseModel


class EventModel(BaseModel):
    __event_name__: ClassVar[LiteralString]


T = TypeVar("T", bound=EventModel)
