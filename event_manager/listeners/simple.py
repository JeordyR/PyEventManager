import inspect
import logging
from collections.abc import Callable
from concurrent.futures import Future
from multiprocessing import Process
from typing import Any, TypeVar

from event_manager.models import EventModel

logger = logging.getLogger("event_manager")

T = TypeVar("T", bound=EventModel)


def _wrapper(_func: Callable[[T], Any], _future: Future, event: T):
    """
    Wrapper function to run the function and store the result in the future.

    Args:
        _func (Callable): Function to run.
        _future (Future): Future to store the result in.
    """
    if _future.set_running_or_notify_cancel():
        try:
            if inspect.getfullargspec(_func).args:
                _future.set_result(_func(event))
            else:
                _future.set_result(_func())  # type: ignore
        except Exception as e:
            _future.set_exception(e)


class Listener:
    def __init__(self, event: str | type[EventModel], func: Callable[[T], Any]):
        """
        Class for a basic listener in the event management system.

        Args:
            event (str): Event to match on.
            func (Callable): Function to call when listener triggers on a matching event.
        """
        self.event = event
        self.func = func

    def __call__(self, event: EventModel) -> Future:
        """
        Call invocation for the obejct, creates and runs a new process with the stored function.

        Args:
            pool (Executor): Executor to run the function in.
        """
        logger.debug(f"Listener running func: {self.func.__name__}")

        future = Future()

        Process(
            target=_wrapper,
            daemon=False,
            args=(),
            kwargs={
                "_func": self.func,
                "_future": future,
                "event": event,
            },
        ).start()

        return future
