import logging
from collections.abc import Callable
from datetime import timedelta
from multiprocessing import Event as EventInit
from multiprocessing import Process
from multiprocessing.synchronize import Event

logger = logging.getLogger("event_manager")


def run(_interval: timedelta, _func: Callable, _event: Event, *args, **kwargs):
    """
    Run the provided function on the provided interval.

    Args:
        _interval (timedelta): Inteveral to run the stored function.
        _func (Callable): Function to run on schedule.
        _event (Event): Event to check for stop conditions.
    """
    logger.info(f"Starting {_func.__name__} to run on schedule: {_interval}.")
    while not _event.wait(_interval.total_seconds()):
        logger.debug(f"Running {_func.__name__} on schedule.")
        _func(*args, **kwargs)


class ScheduledListener:
    def __init__(
        self,
        interval: timedelta,
        func: Callable,
    ):
        """
        Class for a basic listener in the event management system.

        Args:
            interval (timedelta): Schedule to run the functino on.
            func (Callable): Function to call on provided interval.
        """
        self.interval = interval
        self.func = func
        self.sync_event: Event = EventInit()

    def __call__(self):
        """
        Call invocation for the obejct, creates and runs a new process with the stored function.

        Arguments in the call are passed through to the stored function.

        Args:
            pool (Executor): Executor to run the function in.
        """
        logger.debug(f"Executing {self.func.__name__}... Set to run every {self.interval.total_seconds()} seconds.")

        kwargs = {
            "_interval": self.interval,
            "_func": self.func,
            "_event": self.sync_event,
        }

        Process(target=run, daemon=True, kwargs=kwargs).start()

    def stop(self):
        """
        Stop the scheduled listener.
        """
        logger.debug(f"Stopping {self.func.__name__} from running on schedule.")
        self.sync_event.set()
