import abc
from datetime import datetime
from typing import Any


class QueueInterface(abc.ABC):
    last_updated: datetime | None

    @abc.abstractmethod
    def __len__(self) -> int:
        pass

    @abc.abstractmethod
    def empty(self) -> bool:
        pass

    @abc.abstractmethod
    def get(self) -> Any:
        pass

    @abc.abstractmethod
    def get_all(self) -> list[Any]:
        pass

    @abc.abstractmethod
    def put(self, data):
        pass
