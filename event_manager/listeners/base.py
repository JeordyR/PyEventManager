from abc import ABC, abstractmethod
from collections.abc import Callable
from multiprocessing import Process
from threading import Thread


class BaseListener(ABC):
    func: Callable
    event: str
    fork_type: type[Thread | Process]

    @abstractmethod
    def __call__(self, *args, **kwargs):
        pass
