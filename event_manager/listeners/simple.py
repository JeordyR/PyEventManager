import inspect
import logging
from collections.abc import Callable
from concurrent.futures import Future

from event_manager.fork_types import ForkType
from event_manager.listeners.base import BaseListener

logger = logging.getLogger("event_manager")


def _wrapper(_func: Callable, _future: Future, *args, **kwargs):
    """
    Wrapper function to run the function and store the result in the future.

    Args:
        _func (Callable): Function to run.
        _future (Future): Future to store the result in.
    """
    if _future.set_running_or_notify_cancel():
        try:
            if inspect.getfullargspec(_func).args or inspect.getfullargspec(_func).kwonlyargs:
                _future.set_result(_func(*args, **kwargs))
            else:
                _future.set_result(_func())
        except Exception as e:
            _future.set_exception(e)


class Listener(BaseListener):
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

    def __call__(self, *args, **kwargs) -> Future:
        """
        Call invocation for the obejct, creates and runs a new fork with the stored function.

        Arguments in the call are passed through to the stored function.

        Args:
            pool (Executor): Executor to run the function in.
        """
        logger.debug(f"Listener running func: {self.func.__name__}")

        future = Future()

        self.fork_type.value(
            target=_wrapper,
            daemon=False,
            args=args,
            kwargs={
                "_func": self.func,
                "_future": future,
                **kwargs,
            },
        ).start()

        return future
