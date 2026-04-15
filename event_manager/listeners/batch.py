import logging
import time
from collections.abc import Callable
from concurrent.futures import Future
from datetime import datetime
from threading import Thread
from typing import Any

from event_manager.listeners.base import _wrapper
from event_manager.models import EventModel, T
from event_manager.queues.base import QueueInterface
from event_manager.queues.memory import ThreadQueue

logger = logging.getLogger("event_manager")


def batch_input(
    batch_count: int,
    batch_idle_window: int,
    batch_window: int,
    queue: QueueInterface,
    callback: Callable[[list[EventModel]], Any],
):
    """
    Function that will run in a thread to batch up the events, then call the stored function to process them.

    Args:
        batch_count (int): How many events to batch up before invoking the function.
        batch_idle_window (int): Batch events until the queue has been idle for time in seconds.
        batch_window (int): How long to batch up events before processing events.
        queue (QueueInterface): Queue used to batch up the events.
        callback (Callable): Function to call to process the events.
    """
    logger.debug(f"Starting batch input for {callback.__name__}...")

    sleep_time = batch_idle_window if batch_idle_window > 0 else 1
    elapsed = 0

    while True:
        time.sleep(sleep_time)
        elapsed += 1

        logger.debug(f"{callback.__name__}: {queue.last_updated=}")

        if batch_count > 0 and len(queue) >= batch_count:
            break
        elif batch_idle_window > 0 and queue.last_updated:
            since_last = datetime.now() - queue.last_updated
            since_last = since_last.seconds
            logger.debug(f"{callback.__name__}: {since_last=}")

            if since_last >= batch_idle_window:
                break
            else:
                logger.info(
                    f"Batch data updated too recently for {callback.__name__}, waiting {batch_idle_window} seconds."
                )
        elif batch_window > 0 and batch_window <= elapsed:
            break

    logger.debug(f"Batching complete for {callback.__name__}, executing with {len(queue)} events...")
    return callback(queue.get_all())


class BatchListener:
    """
    A class representing a threaded batch listener in the event management system.
    """

    def __init__(
        self,
        event: str | type[EventModel],
        func: Callable[[list[T]], Any],
        batch_count: int,
        batch_idle_window: int,
        batch_window: int,
        queue_type: type[QueueInterface] = ThreadQueue,
    ):
        """
        A class representing a batch listener in the event management system.

        Batch listeners will queue up input data from emitted events, waiting for `batch_window` of idle time
        before triggering the stored function to the process the batched events.

        Args:
            event (str): Event to match on
            func (Callable): Function to call to process the events.
            fork_type (ForkType, optional): Type of fork to use when running the function. Defaults to PROCESS.
            batch_count (int): How many events to batch up before processing events. If this limit is hit, the batch
                will be processed immediately.
            batch_idle_window (int): When greater than zero, will wait for this many seconds of no new events before
                processing the batch.
            batch_window (int): If greater than zero, will process the batch when this many seconds have passed
                since the first event was added to the batch. Overrides `batch_idle_window`.
            queue_type (type[QueueInterface], optional): Type of queue to use when batching up events.
                Defaults to ThreadQueue.
        """
        self.event = event
        self.batch_count = batch_count
        self.batch_idle_window = batch_idle_window
        self.batch_window = batch_window
        self.func = func
        self.future: Future | None = None
        self.thread: Thread | None = None
        self.queue_type = queue_type
        self.queue = queue_type()

    def new(self):
        """
        Creates a new thread in the object to use for a new invocation of the listener.
        """
        logger.debug(f"Spawning a new process for func: {self.func.__name__}")
        self.future = Future()
        self.thread = Thread(
            target=_wrapper,
            daemon=False,
            kwargs={
                "_func": batch_input,
                "_future": self.future,
                "batch_count": self.batch_count,
                "batch_idle_window": self.batch_idle_window,
                "batch_window": self.batch_window,
                "queue": self.queue,
                "callback": self.func,
            },
        )

    def __call__(self, event: EventModel) -> Future:
        """
        Call invocation for the object. Checks if a thread is already running for this listener. If a thread already
        exists, adds the provided data to the queue. If the listener is not currently running it creates a new fork,
        and passes the data in to start the queue.

        Args:
            event (EventModel): Event to add to the queue.
        """
        if self.thread and self.thread.is_alive():
            logger.debug(f"{self.func.__name__}: adding event to queue.")
            self.queue.put(event)
            return self.future  # pyright: ignore -- new call ensures future will be present at this point
        else:
            logger.debug(f"{self.func.__name__}: spinning up a new thread and putting data in queue.")
            self.queue.put(event)
            self.new()
            self.thread.start()  # pyright: ignore -- new call ensures fork will be present at this point
            return self.future  # pyright: ignore -- new call ensures future will be present at this point
