from __future__ import annotations

import time
from datetime import datetime, timedelta
from threading import Event, Thread
from typing import Callable

import loguru
from pydantic import BaseModel

from .batch_queue import BatchQueue

logger = loguru.logger.bind(name="magenta")


class Listener:
    """
    A simple class representing a listener in the event management system.
    """

    def __init__(self, func: Callable[[BaseModel], None], event: str) -> None:
        """
        A simple class representing a listening in the event management system.

        Args:
            func (Callable): Function to call when listener triggers on a matching event.
            event (str): Event to match on.
        """
        self.func: Callable[[BaseModel], None] = func
        self.event: str = event

    def __call__(self, data: BaseModel):
        """
        Call invocation for the obejct, creates and runs a new thread with the stored function, passing data to it.

        Args:
            data (BaseModel): Data to pass to the invoked, threaded, function.
        """
        logger.debug(f"Listener running func: {self.func.__name__} with data: {data.model_dump()}")
        thread = Thread(target=self.func, args=(data,))
        thread.daemon = True
        thread.start()


class BatchListener(Listener):
    """
    A class representing a batch listener in the event management system.
    """

    def __init__(self, event: str, batch_window: int, func: Callable):
        """
        A class representing a batch listener in the event management system.

        Batch listeners will queue up input data from emitted events, waiting for `batch_window` of idle time
        before triggering the stored function to the process the batched events.

        Args:
            event (str): Event to match on
            batch_window (int): How long to batch up event data when invoked before processing events.
            func (Callable): Function to call to process the events.
        """
        self.event = event
        self.queue = BatchQueue()
        self.batch_window = batch_window
        self.func = func
        self.thread: Thread | None = None

    @staticmethod
    def batch_input(batch_window: int, queue: BatchQueue, callback: Callable):
        """
        Function that will run in a thread to batch up the events, then call the stored function to process them.

        Args:
            batch_window (int): How long to batch up event data when invoked before processing events.
            queue (BatchQueue): Queue used to thread-safely batch up the events.
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

        all_entries = queue.get_all()
        callback(all_entries)

    def new_thread(self):
        """
        Creates a new thread in the object to use for a new invocation of the listener.
        """
        logger.debug(f"Spawning a new thread for func: {self.func.__name__}")
        self.thread = Thread(
            target=self.batch_input,
            kwargs={"batch_window": self.batch_window, "queue": self.queue, "callback": self.func},
        )
        self.thread.daemon = True

    def __call__(self, data: BaseModel):
        """
        Call invocation for the object. Checks if a thread is already running for this listener. If a thread already
        exists, adds the provided data to the batch. If the listener is not currently running it creates a new thread,
        and passes the data in to start the batch.

        Args:
            data (BaseModel): Data to
        """
        if self.thread is not None and self.thread.is_alive:
            logger.debug(f"{self.func.__name__}: adding data {data.model_dump()} to queue.")
            self.queue.put(data)
        else:
            logger.debug(f"{self.func.__name__}: spinning up a new thread and putting data: {data.model_dump()}")
            self.queue.put(data)
            self.new_thread()
            self.thread.start()  # pyright: ignore -- listener.new_thread() ensures thread is not None


class ScheduledListener(Thread):
    """
    A class representing a scheduled/intermittent listener in the event management system.
    """

    def __init__(self, interval: timedelta, func: Callable):
        """
        A class representing a scheduled/intermittent listener in the event management system.

        The provided function will be run on the provided interval in its own thread.

        Args:
            interval (timedelta): Inteveral to run the stored function.
            func (Callable): Function to run on schedule.
        """
        Thread.__init__(self)
        self.stopped = Event()
        self.interval = interval
        self.func = func
        self.daemon = True

    def stop(self):
        """
        Stop the thread.
        """
        logger.info(f"Stopping thread for {self.func.__name__}")
        self.stopped.set()
        self.join()

    def run(self):
        """
        Task that will be run in an infinite loop.
        """
        logger.info(
            f"{self.func.__name__} has started its execution and will run every {self.interval.total_seconds()} seconds"
        )
        while not self.stopped.wait(self.interval.total_seconds()):
            self.func()
