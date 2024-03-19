import logging
from collections.abc import Callable
from multiprocessing import Process
from threading import Thread

from pydantic import BaseModel

from event_manager.listeners.base import BaseListener

logger = logging.getLogger("event_manager")


class Listener(BaseListener):
    func: Callable[[BaseModel], None]
    event: str
    fork_type: type[Thread | Process]

    def __init__(self, event: str, func: Callable[[BaseModel], None], fork_type: type[Thread | Process] = Process):
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

    def __call__(self, data: BaseModel):
        """
        Call invocation for the obejct, creates and runs a new fork with the stored function, passing data to it.

        Args:
            data (BaseModel): Data to pass to the invoked function.
        """
        logger.debug(f"Listener running func: {self.func.__name__} with data: {data.model_dump()}")
        fork = self.fork_type(target=self.func, args=(data,))
        fork.daemon = True
        fork.start()
