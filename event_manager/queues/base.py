import abc
from datetime import datetime
from typing import Any


class QueueInterface(abc.ABC):
    """
    An abstract class that represents a queue. It should not be used directly, but through its concrete subclasses.
    """

    last_updated: datetime | None

    @abc.abstractmethod
    def __len__(self) -> int:
        """Return the length of the queue."""
        pass

    @abc.abstractmethod
    def empty(self) -> bool:
        """Check if the queue is empty."""
        pass

    @abc.abstractmethod
    def get(self) -> Any:
        """Get an item from the queue."""
        pass

    @abc.abstractmethod
    def get_all(self) -> list[Any]:
        """Get and return all items from the queue."""
        pass

    @abc.abstractmethod
    def put(self, data):
        """Put an item into the queue and update the last_updated attribute with current time."""
        pass
