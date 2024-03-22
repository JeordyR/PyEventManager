import inspect
import logging
from collections.abc import Callable

from event_manager.fork_types import ForkType
from event_manager.listeners.base import BaseListener

logger = logging.getLogger("event_manager")


class Listener(BaseListener):
    def __init__(self, event: str, func: Callable, fork_type: ForkType, recursive: bool = False):
        """
        Class for a basic listener in the event management system.

        Args:
            event (str): Event to match on.
            func (Callable): Function to call when listener triggers on a matching event.
            fork_type (ForkType, optional): Type of fork to use when running the function. Defaults to PROCESS.
        """
        self.func = func
        self.event = event
        self.fork_type = fork_type
        self.recursive = recursive

    def __call__(self, *args, **kwargs):
        """
        Call invocation for the obejct, creates and runs a new fork with the stored function.

        Arguments in the call are passed through to the stored function.

        Args:
            pool (Executor): Executor to run the function in.
        """
        logger.debug(f"Listener running func: {self.func.__name__}")

        if inspect.getfullargspec(self.func).args or inspect.getfullargspec(self.func).kwonlyargs:
            self.fork_type.value(target=self.func, daemon=not self.recursive, args=args, kwargs=kwargs).start()
        else:
            self.fork_type.value(target=self.func, daemon=not self.recursive).start()
