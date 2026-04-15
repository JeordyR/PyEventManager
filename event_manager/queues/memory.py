from datetime import datetime
from queue import Queue

from event_manager.models import EventModel


class ThreadQueue(Queue):
    """
    Multithreading FIFO Queue modified to track when the queue was last updated.
    """

    def __init__(self, *args, **kwargs):
        self.last_updated: datetime | None = None
        super().__init__(*args, **kwargs)

    def __len__(self):
        """Return the length of the queue."""
        return self.qsize()

    def get_all(self) -> list[EventModel]:
        """
        Get and return all items from the queue

        Returns:
            list[Any]: List of all items from the queue.
        """
        all: list[EventModel] = []
        while self.qsize() > 0:
            all.append(self.get())

        self.last_updated = None
        return all

    def put(self, event: EventModel):
        """Put an item into the queue and update the last_updated attribute with curernt time."""
        self.last_updated = datetime.now()

        super().put(event)
