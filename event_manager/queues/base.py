from datetime import datetime
from typing import Protocol

from event_manager.models import EventModel


class QueueInterface(Protocol):
    """
    An abstract class that represents a queue. It should not be used directly, but through its concrete subclasses.
    """

    last_updated: datetime | None

    def __len__(self) -> int:
        """Return the length of the queue."""
        ...

    def get_all(self) -> list[EventModel]:
        """Get and return all items from the queue."""
        ...

    def put(self, event: EventModel):
        """Put an item into the queue and update the last_updated attribute with current time."""
        ...
