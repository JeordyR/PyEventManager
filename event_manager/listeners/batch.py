import logging
import time
from collections.abc import Callable
from concurrent.futures import Future
from datetime import datetime
from multiprocessing import Process
from threading import Thread
from typing import Any

from event_manager.fork_types import ForkType
from event_manager.listeners.base import _wrapper
from event_manager.queues.base import QueueInterface
from event_manager.queues.memory import ProcessQueue, ThreadQueue

logger = logging.getLogger("event_manager")


def batch_input(batch_count: int, batch_idle_window: int, batch_window: int, queue: QueueInterface, callback: Callable):
    """
    Function that will run in a thread to batch up the events, then call the stored function to process them.

    Args:
        batch_window (int): How long to batch up event data when invoked before processing events.
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

    logger.debug(f"Batching complete for {callback.__name__}, executing...")
    return callback(queue.get_all())


class BatchListener:
    """
    A class representing a threaded batch listener in the event management system.
    """

    def __init__(
        self,
        event: str,
        fork_type: ForkType,
        func: Callable[[list[Any]], Any],
        batch_count: int,
        batch_idle_window: int,
        batch_window: int,
        queue_type: type[QueueInterface],
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
                                                            Defaults to ProcessQueue.
        """
        self.event = event
        self.batch_count = batch_count
        self.batch_idle_window = batch_idle_window
        self.batch_window = batch_window
        self.func = func
        self.fork_type = fork_type
        self.fork: Thread | Process | None = None
        self.future: Future | None = None
        self.queue_type = queue_type

        # Fix the queue type if set incorrectly with known queue types
        _queue_type = queue_type
        if fork_type == ForkType.THREAD and queue_type == ProcessQueue:
            logger.warning("Threaded batch listeners do not support ProcessQueues, defaulting to ThreadQueue.")
            _queue_type = ThreadQueue
        elif fork_type == ForkType.PROCESS and queue_type == ThreadQueue:
            logger.warning("Process batch listeners do not support ThreadQueues, defaulting to ProcessQueue.")
            _queue_type = ProcessQueue

        self.queue = _queue_type()

    def new(self):
        """
        Creates a new fork in the object to use for a new invocation of the listener.
        """
        logger.debug(f"Spawning a new fork for func: {self.func.__name__}")
        self.future = Future()
        self.fork = self.fork_type.value(
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

    def __call__(self, data: Any) -> Future:
        """
        Call invocation for the object. Checks if a fork is already running for this listener. If a fork already
        exists, adds the provided data to the batch. If the listener is not currently running it creates a new fork,
        and passes the data in to start the batch.

        Args:
            pool (Executor): Executor to run the function in.
            data (Any): Data object to batch up and add to the queue.
        """
        if self.fork and self.fork.is_alive():
            logger.debug(f"{self.func.__name__}: adding data to queue.")
            self.queue.put(data)
            return self.future  # pyright: ignore -- new call ensures future will be present at this point
        else:
            logger.debug(f"{self.func.__name__}: spinning up a new fork and putting data in queue.")
            self.queue.put(data)
            self.new()
            self.fork.start()  # pyright: ignore -- new call ensures fork will be present at this point
            return self.future  # pyright: ignore -- new call ensures future will be present at this point
