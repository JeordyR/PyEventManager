import logging
from collections.abc import Callable
from concurrent.futures import Executor, Future

from event_manager.fork_types import ForkType
from event_manager.listeners.base import BaseListener

logger = logging.getLogger("event_manager")


class Listener(BaseListener):
    func: Callable
    event: str
    fork_type: ForkType

    def __init__(self, event: str, func: Callable, fork_type: ForkType):
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
        self.future: Future | None = None

    def __call__(self, pool: Executor, *args, **kwargs):
        """
        Call invocation for the obejct, creates and runs a new fork with the stored function.

        Arguments in the call are passed through to the stored function.

        Args:
            pool (Executor): Executor to run the function in.
        """
        logger.debug(f"Listener running func: {self.func.__name__}")
        self.future = pool.submit(self.func, *args, **kwargs)
