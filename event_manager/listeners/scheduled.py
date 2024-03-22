import logging
import multiprocessing
import threading
from collections.abc import Callable
from concurrent.futures import Executor, Future
from datetime import timedelta
from multiprocessing.synchronize import Event

from event_manager.fork_types import ForkType
from event_manager.listeners.base import BaseListener

logger = logging.getLogger("event_manager")


def run(_interval: timedelta, _func: Callable, _event: Event | threading.Event, *args, **kwargs):
    """
    Run the provided function on the provided interval.

    Args:
        _interval (timedelta): Inteveral to run the stored function.
        _func (Callable): Function to run on schedule.
        _event (Event | threading.Event): Event to check for stop conditions.
    """
    while not _event.wait(_interval.total_seconds()):
        logger.debug(f"Running {_func.__name__} on schedule.")
        _func(*args, **kwargs)


class ScheduledListener(BaseListener):
    def __init__(
        self,
        interval: timedelta,
        func: Callable,
        fork_type: ForkType,
    ):
        """
        Class for a basic listener in the event management system.

        Args:
            event (str): Event to match on.
            func (Callable): Function to call when listener triggers on a matching event.
            fork_type (ForkType, optional): Type of fork to use when running the function. Defaults to PROCESS.
        """
        self.event = ""
        self.interval = interval
        self.func = func
        self.fork_type = fork_type
        self.sync_event: Event | threading.Event = (
            threading.Event() if fork_type == ForkType.THREAD else multiprocessing.Event()
        )
        self.future: Future | None = None

    def __call__(self, pool: Executor, *args, **kwargs):
        """
        Call invocation for the obejct, creates and runs a new fork with the stored function.

        Arguments in the call are passed through to the stored function.

        Args:
            pool (Executor): Executor to run the function in.
        """
        logger.debug(f"Executing {self.func.__name__}... Set to run every {self.interval.total_seconds()} seconds.")
        kwargs = {
            "_interval": self.interval,
            "_func": self.func,
            "_event": self.sync_event,
            **kwargs,
        }

        self.future = pool.submit(run, *args, **kwargs)

    def stop(self):
        """
        Stop the scheduled listener.
        """
        self.sync_event.set()
        logger.debug(f"Stopping {self.func.__name__} from running on schedule.")
