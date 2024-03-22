"""
EventManager project providing an internal event processing system.
"""

__all__ = ["EventManager"]

import collections
import fnmatch
import logging
from collections.abc import Callable
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from datetime import timedelta

from event_manager.fork_types import ForkType
from event_manager.listeners.base import BaseListener
from event_manager.listeners.batch import BatchListener
from event_manager.listeners.scheduled import ScheduledListener
from event_manager.listeners.simple import Listener
from event_manager.queues.base import QueueInterface
from event_manager.queues.memory import ProcessQueue

logger = logging.getLogger("event_manager")


class EventManager:
    def __init__(self, wildcard: bool = True):
        """
        EventManager class wrapping the overall event management process.

        Args:
            wildcard (bool, optional): If listeners can be registered with wildcard matching. Defaults to True.
        """
        # tree of nodes keeping track of nested events
        self._event_tree = Tree(wildcard=wildcard)

        # flat list of listeners triggerd on "any" event
        self._any_listeners: list[BaseListener] = []
        self._scheduled_listeners: list[ScheduledListener] = []

        # pools for execution
        self.thread_pool = ThreadPoolExecutor()
        self.process_pool = ProcessPoolExecutor()

    def on(
        self,
        event: list[str] | str,
        func: Callable | None = None,
        fork_type: ForkType = ForkType.PROCESS,
        batch: bool = False,
        batch_window: int = 30,
        queue_type: type[QueueInterface] = ProcessQueue,
    ) -> Callable:
        """
        Registers a listener on an event. Provided function will be called when a matching event emits.

        Args:
            event (list[str] | str): Event to match on. Can be a list of events to match on multiple.
            func (Callable | None, optional): Function to call when event occurs. Defaults to None.
            fork_type (ForkType, optional): How the function should be run, either in a new Thread or new Process.
                                            Defaults to ForkType.PROCESS.
            batch (bool, optional): Whether events should be batched. Defaults to False.
            batch_window (int, optional): If batching, how many seconds to batch events for. Batching will wait for
                                            this many seconds of no new events before processing the batched events.
                                            Defaults to 30.
            queue_type (type[QueueInterface], optional): Type of Queue to use to abtch events. Defaults to ProcessQueue.

        Returns:
            Callable: Returns the registered function, for use in decorators.
        """
        if isinstance(event, str):
            event = [event]

        def _on(func: Callable) -> Callable:
            for e in event:
                logger.info(f"Registered function {func.__name__} to run on {e} event.")
                if batch:
                    self._event_tree.add_listener(
                        BatchListener(
                            event=e,
                            batch_window=batch_window,
                            func=func,
                            fork_type=fork_type,
                            queue_type=queue_type,
                        )
                    )
                else:
                    self._event_tree.add_listener(Listener(func=func, event=e, fork_type=fork_type))

            return func

        return _on(func) if func else _on

    def on_any(
        self,
        func: Callable | None = None,
        fork_type: ForkType = ForkType.PROCESS,
        batch: bool = False,
        batch_window: int = 30,
        queue_type: type[QueueInterface] = ProcessQueue,
    ) -> Callable:
        """
        Registers a function that listens to all events. Function will be run on all events in the system.

        Args:
            func (Callable | None, optional): Function to call when any event occurs. Defaults to None.
            fork_type (ForkType, optional): How the function should be run, either in a new Thread or new Process.
                                            Defaults to ForkType.PROCESS.
            batch (bool, optional): Whether events should be batched. Defaults to False.
            batch_window (int, optional): If batching, how many seconds to batch events for. Batching will wait for
                                            this many seconds of no new events before processing the batched events.
                                            Defaults to 30.
            queue_type (type[QueueInterface], optional): Type of Queue to use to abtch events. Defaults to ProcessQueue.

        Returns:
            Callable: Returns the registered function, for use in decorators.
        """

        def _on_any(func: Callable) -> Callable:
            logger.info(f"Registered function {func.__name__} to run on ANY event.")
            if batch:
                self._event_tree.add_listener(
                    BatchListener(
                        event="*",
                        batch_window=batch_window,
                        func=func,
                        fork_type=fork_type,
                        queue_type=queue_type,
                    )
                )
            else:
                self._event_tree.add_listener(Listener(func=func, event="*", fork_type=fork_type))

            return func

        return _on_any(func) if func else _on_any

    def schedule(
        self,
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

            if fork_type == ForkType.THREAD:
                listener(self.thread_pool)
            else:
                listener(self.process_pool)

            self._scheduled_listeners.append(listener)
            return func

        return schedule(func) if func else schedule

    def batch_listeners(self, event: str) -> list[Callable]:
        """
        Returns all batch listeners for the provided event.

        Args:
            event (str): Event to get batch listeners for.

        Returns:
            list[Callable]: List of batch listeners for the provided event.
        """
        return [
            listener.func for listener in self._event_tree.find_listeners(event) if isinstance(listener, BatchListener)
        ]

    def listeners(self, event: str) -> list[Callable]:
        """
        Returns all functions that are registered to an event.

        Args:
            event (str): Event to get listeners for.

        Returns:
            list[Callable]: List of functions registered to the provided event.
        """
        return [listener.func for listener in self._event_tree.find_listeners(event)]

    def listeners_any(self) -> list[Callable]:
        """
        Returns all functions that are registered to any event.

        Returns:
            list[Callable]: List of functions registered to any event.
        """
        return [listener.func for listener in self._any_listeners]

    def emit(self, event: str, *args, **kwargs) -> list[Future]:
        """
        Emit an event into the system, calling all functions listening for the provided event.

        Args:
            event (str): Event to emit into the system.

        Returns:
            list[Future]: List of futures from the executed listeners.
        """
        listeners = self._event_tree.find_listeners(event=event)

        listeners.extend(self._any_listeners)

        logger.debug(f"{event} event emitted, executing on {len(listeners)} listener functions")

        # call listeners
        futures = []
        for listener in listeners:
            if isinstance(listener, BatchListener):
                if "data" in kwargs:
                    if listener.fork_type == ForkType.THREAD:
                        futures.append(listener(self.thread_pool, data=kwargs["data"]))
                    else:
                        futures.append(listener(self.process_pool, data=kwargs["data"]))
                else:
                    logger.error("BatchListener listener called without data.")
                    raise Exception("BatchListener listener called without data.")
            else:
                if listener.fork_type == ForkType.THREAD:
                    futures.append(listener(self.thread_pool, args=args, kwargs=kwargs))
                else:
                    futures.append(listener(self.process_pool, args=args, kwargs=kwargs))

        return futures


class Node:
    @classmethod
    def str_is_pattern(cls, s: str) -> bool:
        """
        Check if the provided string is a pattern or not.

        Args:
            s (str): String to check for pattern contents.

        Returns:
            bool: If the string is a patter or not
        """
        return "*" in s or "?" in s

    def __init__(self, name: str, wildcard: bool = True):
        """
        A node in the tree representing an event and the listeners subscribing to it.

        Args:
            name (str): Name of the node (event)
            wildcard (bool, optional): Whether wildcard matches on events are respected. Defaults to True.
        """
        self.name: str = name
        self.parent: "Node | Tree | None" = None
        self.children: collections.OrderedDict[str, "Node"] = collections.OrderedDict()
        self.wildcard: bool = wildcard
        self.listeners: list[BaseListener] = []

    def add_child(self, node: "Node") -> "Node":
        """
        Add a child to the node.

        If an existing child already exists with the same name, will add the listeners from the provided node to
        the existing one.

        Args:
            node (Node): Child Node to add

        Returns:
            Node: Returns the node added as a child or the existing node that was extended.
        """
        # Merge listeners when existing node with same name is present
        if node.name in self.children:
            _node = self.children[node.name]

            for listener in node.listeners:
                _node.add_listener(listener)

            return _node
        # Add it and set its parent
        else:
            self.children[node.name] = node
            node.parent = self
            return node

    def add_listener(self, listener: BaseListener):
        """
        Add a listener to this node.

        Args:
            listener (BaseListener): Listener to add to the node
        """
        if listener not in self.listeners:
            self.listeners.append(listener)

    def check_name(self, pattern: str) -> bool:
        """
        Check if the name of this node matches the provided pattern.

        Args:
            pattern (str): Pattern to match the name against.

        Returns:
            bool: Whether the name matched the pattern.
        """
        if self.wildcard:
            if self.str_is_pattern(pattern):
                return fnmatch.fnmatch(self.name, pattern)
            if self.str_is_pattern(self.name):
                return fnmatch.fnmatch(pattern, self.name)

        return self.name == pattern

    def find_nodes(self, event: str | list[str] | tuple[str]) -> list["Node"]:
        """
        Get all nodes, including childen, that match the provided event.

        Event can come in as a string, ie `event.sub.sub2` or split into a list or tuple.

        Returns:
            list["Node"]: List of nodes that match the event.
        """
        # trivial case
        if not event:
            return []

        # parse event
        if isinstance(event, list | tuple):
            pattern, sub_patterns = event[0], event[1:]
        else:
            pattern, *sub_patterns = event.split(".")

        # first make sure that pattern matches _this_ name
        if not self.check_name(pattern):
            return []

        # when there are no sub patterns, return this one
        if not sub_patterns:
            return [self]

        # recursively match sub names with nodes
        return sum((node.find_nodes(event=sub_patterns) for node in self.children.values()), [self])


class Tree:
    def __init__(self, wildcard: bool = True):
        """
        A tree storing Nodes for mapping events to listener functions.

        Args:
            wildcard (bool, optional): Wether events should match wildcards. Defaults to True.
        """
        self.children: collections.OrderedDict[str, Node] = collections.OrderedDict()
        self.wildcard = wildcard

    def find_nodes(self, event: str | list[str] | tuple[str]) -> list[Node]:
        """
        Get all nodes, that match the provided event.

        Event can come in as a string, ie `event.sub.sub2` or split into a list or tuple.

        Returns:
            list["Node"]: List of nodes that match the event.
        """
        return sum((node.find_nodes(event=event) for node in self.children.values()), [])

    def add_listener(self, listener: BaseListener) -> None:
        """
        Add a listener to the tree. Either add a new Node to the tree or add the listener into
        the tree at the appropriate Node if it already exists.

        Args:
            listener (BaseListener): Listener to add to the tree.
        """
        # add nodes without evaluating wildcards, this is done during node lookup only
        names = listener.event.split(".")

        # lookup the deepest existing parent
        node = self
        while names:
            name = names.pop(0)
            if name in node.children:
                node = node.children[name]
            else:
                new_node = Node(name=name, wildcard=self.wildcard)
                node.add_child(new_node)
                node = new_node

        # add the listeners
        node.add_listener(listener)

    def add_child(self, node: Node) -> Node:
        """
        Add a child Node directly to the tree. If a node with the same name already exists, the listeners from the
        provided Node will be merged into the existing.

        Args:
            node (Node): Node to add to the tree.

        Returns:
            Node: Node added to the tree, or the existing Node that was extended.
        """
        # Merge listeners when existing node with same name is present
        if node.name in self.children:
            _node = self.children[node.name]
            _node.listeners.extend(node.listeners)
            return _node
        # Add it and set its parent
        else:
            self.children[node.name] = node
            node.parent = self
            return node

    def find_listeners(self, event: str) -> list[BaseListener]:
        """
        Get all listener functions from the nodes that match the provided event.

        Args:
            event (str): Event to match against.

        Returns:
            list[Listener]: List of all listeners that should be invoked for the provided event.
        """
        listeners = sum((node.listeners for node in self.find_nodes(event)), [])
        return listeners
