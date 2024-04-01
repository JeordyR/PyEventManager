import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from concurrent.futures import Future

from event_manager.fork_types import ForkType


class BaseListener(ABC):
    """
    An abstract class that represents a listener. It should not be used directly, but through its concrete subclasses.
    """

    func: Callable
    event: str
    fork_type: ForkType

    @abstractmethod
    def __call__(self, *args, **kwargs) -> Future:
        raise NotImplementedError()


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
