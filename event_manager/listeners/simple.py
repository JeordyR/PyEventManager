import logging
from collections.abc import Callable
from concurrent.futures import Future
from threading import Thread
from typing import Any, TypeVar

from event_manager.listeners.base import _wrapper
from event_manager.models import EventModel

logger = logging.getLogger("event_manager")

T = TypeVar("T", bound=EventModel)


class Listener:
    def __init__(self, func: Callable[[T], Any]):
        """
        Class for a basic listener in the event management system.

        Args:
            event (str): Event to match on.
            func (Callable): Function to call when listener triggers on a matching event.
        """
        self.func = func

    def __call__(self, event: EventModel) -> Future:
        """
        Call invocation for the obejct, creates and runs a new thread with the stored function.

        Args:
            event (EventModel): Event to pass to the stored function.
        """
        logger.debug(f"Listener running func: {self.func.__name__}")

        future = Future()

        Thread(
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
