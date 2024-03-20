import logging
import multiprocessing
import threading
from collections.abc import Callable
from datetime import timedelta
from multiprocessing.synchronize import Event

from event_manager.listeners.base import BaseListener

logger = logging.getLogger("event_manager")


def run(_interval: timedelta, _func: Callable, _event: Event | threading.Event, *args, **kwargs):
    """
    Run the provided function on the provided interval.

    Args:
        interval (timedelta): Inteveral to run the stored function.
        func (Callable): Function to run on schedule.
    """
    while not _event.wait(_interval.total_seconds()):
        logger.debug(f"Running {_func.__name__} on schedule.")
        _func(*args, **kwargs)


class ScheduledListener(BaseListener):
    def __init__(
        self,
        interval: timedelta,
        func: Callable,
        fork_type: type[threading.Thread | multiprocessing.Process] = multiprocessing.Process,
    ):
        """
        Class for a basic listener in the event management system.

        Args:
            event (str): Event to match on.
            func (Callable): Function to call when listener triggers on a matching event.
            fork_type (type[Thread | Process], optional): Type of fork to use when running the function.
                                                            Defaults to Process.
        """
        self.event = ""
        self.interval = interval
        self.func = func
        self.fork_type = fork_type
        self.sync_event: Event | threading.Event = (
            threading.Event() if fork_type == threading.Thread else multiprocessing.Event()
        )

    def __call__(self, *args, **kwargs):
        """
        Call invocation for the obejct, creates and runs a new fork with the stored function.

        Arguments in the call are passed through to the stored function.
        """
        logger.debug(f"Executing {self.func.__name__}... Set to run every {self.interval.total_seconds()} seconds.")
        fork = self.fork_type(
            target=run,
            args=args,
            kwargs={
                "_interval": self.interval,
                "_func": self.func,
                "_event": self.sync_event,
                **kwargs,
            },
        )
        fork.daemon = True
        fork.start()

    def stop(self):
        """
        Stop the scheduled listener.
        """
        self.sync_event.set()
        logger.debug(f"Stopping {self.func.__name__} from running on schedule.")
