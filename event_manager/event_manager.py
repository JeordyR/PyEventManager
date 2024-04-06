"""
EventManager project providing an internal event processing system.
"""

__all__ = ["EventManager"]

import logging
from collections.abc import Callable
from concurrent.futures import Future
from datetime import timedelta

from event_manager.fork_types import ForkType
from event_manager.listeners.batch import BatchListener
from event_manager.listeners.scheduled import ScheduledListener
from event_manager.listeners.simple import Listener
from event_manager.queues.base import QueueInterface
from event_manager.queues.memory import ProcessQueue
from event_manager.tree import Tree

logger = logging.getLogger("event_manager")


class EventManager:
    _event_tree = Tree()
    _scheduled_listeners: list[ScheduledListener] = []

    @classmethod
    def on(
        cls,
        event: list[str] | str,
        func: Callable | None = None,
        fork_type: ForkType = ForkType.PROCESS,
    ):
        if isinstance(event, str):
            event = [event]

        def _on(func: Callable) -> Callable:
            for e in event:
                logger.info(f"Registered function {func.__name__} to run on {e} event.")
                cls._event_tree.add_data(name=e, data=Listener(func=func, event=e, fork_type=fork_type))

            return func

        return _on(func) if func else _on

    @classmethod
    def on_batch(
        cls,
        event: list[str] | str,
        func: Callable | None = None,
        fork_type: ForkType = ForkType.PROCESS,
        batch_count: int = 0,
        batch_idle_window: int = 0,
        batch_window: int = 30,
        queue_type: type[QueueInterface] = ProcessQueue,
    ):
        if isinstance(event, str):
            event = [event]

        def _on_batch(func: Callable) -> Callable:
            for e in event:
                logger.info(f"Registered function {func.__name__} to run on {e} event.")
                cls._event_tree.add_data(
                    name=e,
                    data=BatchListener(
                        event=e,
                        func=func,
                        fork_type=fork_type,
                        batch_count=batch_count,
                        batch_idle_window=batch_idle_window,
                        batch_window=batch_window,
                        queue_type=queue_type,
                    ),
                )

            return func

        return _on_batch(func) if func else _on_batch

    @classmethod
    def schedule(
        cls,
        interval: timedelta,
        func: Callable[[None], None] | None = None,
        fork_type: ForkType = ForkType.PROCESS,
    ) -> Callable:
        """
        Registers a scheduled function that will be executed on the specified interval.

        Args:
            interval (timedelta): Timedelta object specifying the interval to run the function
            func (Callable): Function to call on a schedule
            fork_type (ForkType, optional): How the function should be run, either in a new Thread or new Process.
                                            Defaults to ForkType.PROCESS.
        Returns:
            Callable: Returns the registered function, for use in decorators.
        """

        def schedule(func: Callable) -> Callable:
            logger.info(f"Scheduling {func.__name__} to run every {interval.total_seconds()} seconds.")
            listener = ScheduledListener(interval=interval, func=func, fork_type=fork_type)
            listener()
            cls._scheduled_listeners.append(listener)
            return func

        return schedule(func) if func else schedule

    @classmethod
    def listeners(cls, event: str) -> list[Callable]:
        """
        Returns all functions that are registered to an event.

        Args:
            event (str): Event to get listeners for.

        Returns:
            list[Callable]: List of functions registered to the provided event.
        """
        return [listener.func for listener in cls._event_tree.find_data(event)]

    @classmethod
    def emit(cls, event: str, *args, **kwargs) -> list[Future]:
        """
        Emit an event into the system, calling all functions listening for the provided event.

        Args:
            event (str): Event to emit into the system.

        Returns:
            list[Future]: List of futures from the executed listeners.
        """
        listeners = cls._event_tree.find_data(name=event)

        logger.debug(f"{event} event emitted, executing on {len(listeners)} listener functions")

        futures = []

        # call listeners
        for listener in listeners:
            try:
                if isinstance(listener, BatchListener):
                    if "data" in kwargs:
                        futures.append(listener(data=kwargs["data"]))
                    else:
                        logger.error("BatchListener listener called without data.")
                        raise Exception("BatchListener listener called without data.")
                else:
                    futures.append(listener(*args, **kwargs))
            except Exception as e:
                print(f"Exception in emit: {e}")
                logger.error(f"Error executing listener {listener.func.__name__} for event {event}.")
                logger.error(e)

        return futures
