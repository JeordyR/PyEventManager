import logging
import time
from collections.abc import Callable
from datetime import datetime
from multiprocessing import Process
from threading import Thread
from typing import Any

from event_manager.listeners.base import BaseListener
from event_manager.queues.base import QueueInterface
from event_manager.queues.memory import ProcessQueue, ThreadQueue

logger = logging.getLogger("event_manager")


def batch_input(batch_window: int, queue: QueueInterface, callback: Callable):
    """
    Function that will run in a thread to batch up the events, then call the stored function to process them.

    Args:
        batch_window (int): How long to batch up event data when invoked before processing events.
        queue (BatchThreadQueue | BatchProcessQueue): Queue used to batch up the events.
        callback (Callable): Function to call to process the events.
    """
    while True:
        time.sleep(batch_window)

        logger.debug(f"{callback.__name__}: {queue.last_updated=}")
        if queue.last_updated:
            since_last = datetime.now() - queue.last_updated
            since_last = since_last.seconds
            logger.debug(f"{callback.__name__}: {since_last=}")

            if since_last > batch_window:
                break
            else:
                logger.info(
                    f"Batch data updated too recently for func {callback.__name__}, waiting {batch_window} seconds."
                )

    callback(queue.get_all())


class BatchListener(BaseListener):
    """
    A class representing a threaded batch listener in the event management system.
    """

    def __init__(
        self,
        event: str,
        batch_window: int,
        func: Callable[[list[Any]], None],
        fork_type: type[Thread | Process] = Process,
        queue_type: type[QueueInterface] = ProcessQueue,
    ):
        """
        A class representing a batch listener in the event management system.

        Batch listeners will queue up input data from emitted events, waiting for `batch_window` of idle time
        before triggering the stored function to the process the batched events.

        Args:
            event (str): Event to match on
            batch_window (int): How long to batch up event data when invoked before processing events.
            func (Callable): Function to call to process the events.
            fork_type (type[Thread | Process], optional): Type of fork to use when running the function.
                                                            Defaults to Process.
        """
        self.event = event
        self.batch_window = batch_window
        self.func = func
        self.fork: Thread | Process | None = None
        self.fork_type: type[Thread | Process] = fork_type
        self.queue_type: type[QueueInterface] = queue_type

        # Fix the queue type if set incorrectly with known queue types
        _queue_type = queue_type
        if fork_type == Thread and queue_type == ProcessQueue:
            logger.warning("Threaded batch listeners do not support ProcessQueues, defaulting to ThreadQueue.")
            _queue_type = ThreadQueue
        elif fork_type == Process and queue_type == ThreadQueue:
            logger.warning("Process batch listeners do not support ThreadQueues, defaulting to ProcessQueue.")
            _queue_type = ProcessQueue

        self.queue = _queue_type()

    def new(self):
        """
        Creates a new fork in the object to use for a new invocation of the listener.
        """
        logger.debug(f"Spawning a new fork for func: {self.func.__name__}")
        self.fork = self.fork_type(
            target=batch_input,
            kwargs={"batch_window": self.batch_window, "queue": self.queue, "callback": self.func},
        )
        self.fork.daemon = True

    def __call__(self, data: Any):
        """
        Call invocation for the object. Checks if a fork is already running for this listener. If a fork already
        exists, adds the provided data to the batch. If the listener is not currently running it creates a new fork,
        and passes the data in to start the batch.

        Args:
            data (Any): Data object to add to the queue.
        """
        if self.fork is not None and self.fork.is_alive:
            logger.debug(f"{self.func.__name__}: adding data {data.model_dump()} to queue.")
            self.queue.put(data)
        else:
            logger.debug(f"{self.func.__name__}: spinning up a new fork and putting data: {data.model_dump()}")
            self.queue.put(data)
            self.new()
            self.fork.start()  # pyright: ignore -- listener.new() ensures fork is not None
