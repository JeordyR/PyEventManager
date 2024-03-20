import queue
from datetime import datetime
from multiprocessing.queues import Queue
from typing import Any

from event_manager.queues.base import QueueInterface


class ThreadQueue(QueueInterface, queue.SimpleQueue):
    """
    Simple, unbound FIFO Queue used for Threading, modified to track when the queue was last updated.
    """

    def __init__(self, *args, **kwargs):
        self.last_updated: datetime | None = None

        super().__init__(*args, **kwargs)

    def __len__(self):
        return self.qsize()

    def empty(self) -> bool:
        return super().empty()

    def put(self, *args, **kwargs):
        self.last_updated = datetime.now()

        super().put(*args, **kwargs)

    def get(self) -> Any:
        return super().get()

    def get_all(self) -> list[Any]:
        """
        Get and return all items from the queue

        Returns:
            list[Any]: List of all items from the queue.
        """
        all = []
        while self.qsize() > 0:
            all.append(self.get())

        self.last_updated = None
        return all


class ProcessQueue(QueueInterface, Queue):
    """
    Multiprocessing FIFO Queue modified to track when the queue was last updated.
    """

    def __init__(self, *args, **kwargs):
        self.last_updated: datetime | None = None

        super().__init__(*args, **kwargs)

    def __len__(self):
        return self.qsize()

    def empty(self) -> bool:
        return super().empty()

    def put(self, *args, **kwargs):
        self.last_updated = datetime.now()

        super().put(*args, **kwargs)

    def get(self) -> Any:
        return super().get()

    def get_all(self) -> list[Any]:
        """
        Get and return all items from the queue

        Returns:
            list[Any]: List of all items from the queue.
        """
        all = []
        while self.qsize() > 0:
            all.append(self.get())

        self.last_updated = None
        return all
