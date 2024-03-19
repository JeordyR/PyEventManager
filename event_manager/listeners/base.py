from abc import ABC, abstractmethod
from collections.abc import Callable
from multiprocessing import Process
from threading import Thread

from pydantic import BaseModel


class BaseListener(ABC):
    func: Callable
    event: str
    fork_type: type[Thread | Process]

    @abstractmethod
    def __call__(self, data: BaseModel):
        pass
