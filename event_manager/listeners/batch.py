import logging
import time
from collections.abc import Callable
from concurrent.futures import Executor, Future
from datetime import datetime
from typing import Any

from event_manager.fork_types import ForkType
from event_manager.listeners.base import BaseListener
from event_manager.queues.base import QueueInterface
from event_manager.queues.memory import ProcessQueue, ThreadQueue

logger = logging.getLogger("event_manager")


def batch_input(batch_window: int, queue: QueueInterface, callback: Callable) -> Any:
    """
    Function that will run in a thread to batch up the events, then call the stored function to process them.

    Args:
        batch_window (int): How long to batch up event data when invoked before processing events.
        queue (QueueInterface): Queue used to batch up the events.
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

    return callback(queue.get_all())


class BatchListener(BaseListener):
    """
    A class representing a threaded batch listener in the event management system.
    """

    def __init__(
        self,
        event: str,
        batch_window: int,
        func: Callable[[list[Any]], Any],
        fork_type: ForkType,
        queue_type: type[QueueInterface],
    ):
        """
        A class representing a batch listener in the event management system.

        Batch listeners will queue up input data from emitted events, waiting for `batch_window` of idle time
        before triggering the stored function to the process the batched events.

        Args:
            event (str): Event to match on
            batch_window (int): How long to batch up event data when invoked before processing events.
            func (Callable): Function to call to process the events.
            fork_type (ForkType, optional): Type of fork to use when running the function. Defaults to PROCESS.
            queue_type (type[QueueInterface], optional): Type of queue to use when batching up events.
                                                            Defaults to ProcessQueue.
        """
        self.event = event
        self.batch_window = batch_window
        self.func = func
        self.fork_type = fork_type
        self.queue_type = queue_type
        self.future: Future | None = None

        # Fix the queue type if set incorrectly with known queue types
        _queue_type = queue_type
        if fork_type == ForkType.THREAD and queue_type == ProcessQueue:
            logger.warning("Threaded batch listeners do not support ProcessQueues, defaulting to ThreadQueue.")
            _queue_type = ThreadQueue
        elif fork_type == ForkType.PROCESS and queue_type == ThreadQueue:
            logger.warning("Process batch listeners do not support ThreadQueues, defaulting to ProcessQueue.")
            _queue_type = ProcessQueue

        self.queue = _queue_type()

    def __call__(self, pool: Executor, data: Any):
        """
        Call invocation for the object. Checks if a fork is already running for this listener. If a fork already
        exists, adds the provided data to the batch. If the listener is not currently running it creates a new fork,
        and passes the data in to start the batch.

        Args:
            pool (Executor): Executor to run the function in.
            data (Any): Data object to batch up and add to the queue.
        """
        if self.future and self.future.running():
            logger.debug(f"{self.func.__name__}: adding data to queue.")
            self.queue.put(data)
        else:
            logger.debug(f"{self.func.__name__}: spinning up a new fork and putting data in queue.")
            self.queue.put(data)
            self.future = pool.submit(batch_input, batch_window=self.batch_window, queue=self.queue, callback=self.func)
