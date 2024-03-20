import logging
from collections.abc import Callable
from multiprocessing import Process
from threading import Thread

from event_manager.listeners.base import BaseListener

logger = logging.getLogger("event_manager")


class Listener(BaseListener):
    func: Callable
    event: str
    fork_type: type[Thread | Process]

    def __init__(self, event: str, func: Callable, fork_type: type[Thread | Process] = Process):
        """
        Class for a basic listener in the event management system.

        Args:
            event (str): Event to match on.
            func (Callable): Function to call when listener triggers on a matching event.
            fork_type (type[Thread | Process], optional): Type of fork to use when running the function.
                                                            Defaults to Process.
        """
        self.func = func
        self.event = event
        self.fork_type = fork_type

    def __call__(self, *args, **kwargs):
        """
        Call invocation for the obejct, creates and runs a new fork with the stored function.

        Arguments in the call are passed through to the stored function.
        """
        logger.debug(f"Listener running func: {self.func.__name__}")
        fork = self.fork_type(target=self.func, args=args, kwargs=kwargs)
        fork.daemon = True
        fork.start()
