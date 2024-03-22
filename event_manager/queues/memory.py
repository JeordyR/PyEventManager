from datetime import datetime

# from multiprocessing.queues import Queue
from multiprocessing import get_context
from multiprocessing.queues import Queue as ProcessingQueueBase
from queue import SimpleQueue as ThreadQueueBase
from typing import Any

from event_manager.queues.base import QueueInterface


class ThreadQueue(QueueInterface, ThreadQueueBase):
    """
    Simple, unbound FIFO Queue used for Threading, modified to track when the queue was last updated.
    """

    def __init__(self, *args, **kwargs):
        self.last_updated: datetime | None = None
        ThreadQueueBase.__init__(self, *args, **kwargs)

    def __len__(self):
        """Return the length of the queue."""
        return self.qsize()

    def empty(self) -> bool:
        """Check if the queue is empty."""
        return ThreadQueueBase.empty(self)

    def put(self, *args, **kwargs):
        """Put an item into the queue and update the last_updated attribute with curernt time."""
        self.last_updated = datetime.now()

        ThreadQueueBase.put(self, *args, **kwargs)

    def get(self) -> Any:
        """Get an item from the queue."""
        return ThreadQueueBase.get(self)

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


class ProcessQueue(QueueInterface, ProcessingQueueBase):
    """
    Multiprocessing FIFO Queue modified to track when the queue was last updated.
    """

    def __init__(self, *args, **kwargs):
        self.last_updated: datetime | None = None
        ProcessingQueueBase.__init__(self, *args, **kwargs, ctx=get_context())

    def __len__(self):
        """Return the length of the queue."""
        return self.qsize()

    def empty(self) -> bool:
        """Check if the queue is empty."""
        return ProcessingQueueBase.empty(self)

    def put(self, *args, **kwargs):
        """Put an item into the queue and update the last_updated attribute with curernt time."""
        self.last_updated = datetime.now()

        ProcessingQueueBase.put(self, *args, **kwargs)

    def get(self) -> Any:
        """Get an item from the queue."""
        return ProcessingQueueBase.get(self)

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
