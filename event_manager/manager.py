"""
EventManager project providing an internal event processing system.
"""

__all__ = ["EventManager"]

import logging
from collections.abc import Callable
from concurrent.futures import Future
from datetime import timedelta
from typing import Any

from event_manager.listeners.batch import BatchListener
from event_manager.listeners.scheduled import ScheduledListener
from event_manager.listeners.simple import Listener
from event_manager.models import EventModel, T
from event_manager.queues.base import QueueInterface
from event_manager.queues.memory import ThreadQueue
from event_manager.tree import Tree

logger = logging.getLogger("event_manager")


class EventManager:
    _event_tree = Tree()
    _scheduled_listeners: list[ScheduledListener] = []

    @classmethod
    def on(
        cls,
        event: list[str] | str | type[T] | list[type[T]],
    ) -> Callable[[Callable[[T], Any]], Callable[[T], Any]]:
        """
        Registers a function that will run immediately on any matched event.

        Args:
            event (list[str] | str | type[T] | list[type[T]]): Event(s) to match on.

        Returns:
            Callable[[Callable[[T], Any]], Callable[[T], Any]]: Returns the registered function.
        """
        events = []

        if isinstance(event, str):
            events = [event]
        elif isinstance(event, list):
            for item in event:
                if isinstance(item, str):
                    events.append(item)
                elif issubclass(item, EventModel):
                    events.append(item.__event_name__)
                else:
                    raise TypeError(f"{type(item)} is not a supported type for event definition.")
        elif issubclass(event, EventModel):
            events = [event.__event_name__]
        else:
            raise TypeError(f"{type(item)} is not a supported type for event definition.")

        def decorator(func: Callable[[T], Any]) -> Callable[[T], Any]:
            for e in events:
                logger.info(f"Registered function {func.__name__} to run on {e} event.")
                cls._event_tree.add_listener(node_name=e, listener=Listener(func=func))

            return func

        return decorator

    @classmethod
    def on_batch(
        cls,
        event: list[str] | str | type[T] | list[type[T]],
        batch_count: int = 0,
        batch_idle_window: int = 0,
        batch_window: int = 30,
        queue_type: type[QueueInterface] = ThreadQueue,
    ) -> Callable[[Callable[[list[EventModel]], Any]], Callable[[list[EventModel]], Any]]:
        """
        Registers a function that will batch up events and only execute when the configured conditions have been met.

        Args:
            event (list[str] | str | type[T] | list[type[T]]): Event(s) to match on.
            batch_count (int, optional): How many events to batch up before processing events.
                If this limit is hit, the batch will be processed immediately. Defaults to 0.
            batch_idle_window (int, optional): When greater than zero, will wait for this many seconds of no new events
                before processing the batch. Defaults to 0.
            batch_window (int, optional): If greater than zero, will process the batch when this many seconds have
                passed since the first event was added to the batch. Overrides `batch_idle_window`. Defaults to 30.
            queue_type (type[QueueInterface], optional): Type of queue to use when batching up events.
                Defaults to ThreadQueue.

        Returns:
            Callable[[Callable[[list[T]], Any]], Callable[[list[T]], Any]]: Returns the registered function.
        """
        events = []

        if isinstance(event, str):
            events = [event]
        elif isinstance(event, list):
            for item in event:
                if isinstance(item, str):
                    events.append(item)
                elif issubclass(item, EventModel):
                    events.append(item.__event_name__)
                else:
                    raise TypeError(f"{type(item)} is not a supported type for event definition.")
        elif issubclass(event, EventModel):
            events = [event.__event_name__]
        else:
            raise TypeError(f"{type(item)} is not a supported type for event definition.")

        events = list(dict.fromkeys(events))

        def decorator(func: Callable[[list[EventModel]], Any]) -> Callable[[list[EventModel]], Any]:
            listener = BatchListener(
                func=func,
                batch_count=batch_count,
                batch_idle_window=batch_idle_window,
                batch_window=batch_window,
                queue_type=queue_type,
            )

            for e in events:
                logger.info(f"Registered function {func.__name__} to run on {e} event.")
                cls._event_tree.add_listener(node_name=e, listener=listener)

            return func

        return decorator

    @classmethod
    def schedule(
        cls,
        interval: timedelta,
    ) -> Callable[[Callable[[], None]], Callable[[], None]]:
        """
        Registers a scheduled function that will be executed on the specified interval.

        Args:
            interval (timedelta): Timedelta object specifying the interval to run the function

        Returns:
            Callable[[Callable[[], None]], Callable[[], None]]: _description_
        """

        def decorator(func: Callable[[], None]) -> Callable[[], None]:
            logger.info(f"Scheduling {func.__name__} to run every {interval.total_seconds()} seconds.")
            listener = ScheduledListener(interval=interval, func=func)
            listener()
            cls._scheduled_listeners.append(listener)

            return func

        return decorator

    @classmethod
    def listeners(cls, event: str | type[EventModel]) -> list[Callable]:
        """
        Returns all functions that are registered to an event or event pattern.

        Args:
            event (str): Event to get listeners for.

        Returns:
            list[Callable]: List of functions registered to the provided event.
        """
        event_name = ""
        if isinstance(event, str):
            event_name = event
        elif issubclass(event, EventModel):
            event_name = event.__event_name__
        else:
            raise TypeError(f"{type(event)} is not a supported type for event definition.")

        return [listener for listener in cls._event_tree.find_listeners(event_name)]

    @classmethod
    def emit(cls, event: EventModel) -> list[Future]:
        """
        Emit an event into the system, calling all functions listening for the provided event.

        Args:
            event (EventModel): Event to emit into the system.

        Returns:
            list[Future]: List of futures from the executed listeners.
        """
        event_name = ""
        if isinstance(event, EventModel):
            event_name = event.__event_name__
        else:
            raise TypeError(f"{type(event)} is not a supported type for event definition.")

        listeners = cls.listeners(event=event.__event_name__)

        logger.debug(f"{event_name} event emitted, executing on {len(listeners)} listener functions")

        futures = []

        # call listeners
        for listener in listeners:
            try:
                futures.append(listener(event))
            except Exception as e:
                logger.error(f"Error executing listener {listener.__name__} for event {event}.")
                logger.error(e)

        return futures
