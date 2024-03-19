from datetime import datetime
from queue import SimpleQueue
from typing import Any


class BatchQueue(SimpleQueue):
    """
    Simple, unbound FIFO Queue modified to track when the queue was last updated.
    """

    def __init__(self, *args, **kwargs):
        self.last_updated: datetime | None = None

        super().__init__(*args, **kwargs)

    def __len__(self):
        return self.qsize()

    def put(self, *args, **kwargs):
        self.last_updated = datetime.now()

        super().put(*args, **kwargs)

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
