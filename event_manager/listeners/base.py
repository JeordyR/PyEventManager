from abc import ABC, abstractmethod
from collections.abc import Callable
from concurrent.futures import Executor, Future

from event_manager.fork_types import ForkType


class BaseListener(ABC):
    func: Callable
    event: str
    fork_type: ForkType
    future: None | Future

    @abstractmethod
    def __call__(self, pool: Executor, *args, **kwargs):
        pass
