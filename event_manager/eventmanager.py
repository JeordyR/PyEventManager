"""
EventManager project providing an internal event processing system.
"""

import collections
import fnmatch
from datetime import timedelta
from typing import Callable

import loguru
from pydantic import BaseModel

from .listeners import BatchListener, Listener, ScheduledListener

logger = loguru.logger.bind(name="magenta")


class EventManager:
    def __init__(self, wildcard: bool = True):
        """
        EventManager class wrapping the overall event management process.

        Args:
            wildcard (bool, optional): If listeners can be registered with wildcard matching on events.
                                        Defaults to True.
        """
        # tree of nodes keeping track of nested events
        self._event_tree = Tree(wildcard=wildcard)

        # flat list of listeners triggerd on "any" event
        self._any_listeners: list[Listener] = []
        self._scheduled_listeners: list[ScheduledListener] = []

    def on(self, event: str, func: Callable[[BaseModel], None] | None = None) -> Callable:
        """
        Registeres a listener on an event. Provided function will be called when a matching event emits.
        """

        def on(func: Callable[[BaseModel], None]) -> Callable[[BaseModel], None]:
            logger.info(f"Registered function {func.__name__} to run on {event} event.")
            self._event_tree.add_listener(Listener(func=func, event=event))
            return func

        return on(func) if func else on

    def on_any(self, func: Callable[[BaseModel], None] | None = None) -> Callable:
        """
        Registers a function that listens to all events. Function will be run on all events in the system.
        """

        def on_any(func: Callable[[BaseModel], None]) -> Callable[[BaseModel], None]:
            logger.info(f"Registered function {func.__name__} to run on ANY event.")
            self._any_listeners.append(Listener(func=func, event="*"))
            return func

        return on_any(func) if func else on_any

    def on_batch(self, event: str, batch_window: int = 30, func: Callable[[BaseModel], None] | None = None) -> Callable:
        """
        Registers a function that will be run in a thread with a queue used to send data to it whenever the event emits.
        """

        def on_batch(func: Callable[[BaseModel], None]) -> Callable[[BaseModel], None]:
            logger.info(
                f"Registered function {func.__name__} to run on {event} event "
                f"with data batched in a {batch_window} second window."
            )
            listener = BatchListener(event=event, batch_window=batch_window, func=func)
            self._event_tree.add_listener(listener)
            return func

        return on_batch(func) if func else on_batch

    def schedule(self, interval: timedelta, func: Callable[[None], None] | None = None) -> Callable:
        """
        Registers a scheduled function that will be executed on the specified interval.

        Args:
            interval (timedelta): Timedelta object specifying the interval to run the function
            func (Callable): Function to call on a schedule
        """

        def schedule(func: Callable) -> Callable:
            logger.info(f"Scheduling {func.__name__} to run every {interval.total_seconds()} seconds.")
            listener = ScheduledListener(interval=interval, func=func)
            listener.start()
            self._scheduled_listeners.append(listener)
            return func

        return schedule(func) if func else schedule

    def listeners(self, event: str) -> list[Callable[[BaseModel], None]]:
        """
        Returns all functions that are registered to an event.
        """
        return [listener.func for listener in self._event_tree.find_listeners(event)]

    def listeners_any(self) -> list[Callable[[BaseModel], None]]:
        """
        Returns all functions that are registered to any event.
        """
        return [listener.func for listener in self._any_listeners]

    def emit(self, event: str, data: BaseModel):
        """
        Emit an event into the system, calling all functions listening for the provided event.

        Args:
            event (str): Event to emit into the system.
        """
        listeners = self._event_tree.find_listeners(event=event)

        listeners.extend(self._any_listeners)

        logger.debug(f"{event} event emitted, executing on {len(listeners)} functions with data: {data.model_dump()}")

        # call listeners
        for listener in listeners:
            listener(data)


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
        self.listeners: list[Listener] = []

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

    def add_listener(self, listener: Listener):
        """
        Add a listener to this node.

        Args:
            listener (Listener): Listener to add to the node
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

    def add_listener(self, listener: Listener) -> None:
        """
        Add a listener to the tree. Either add a new Node to the tree or add the listener into
        the tree at the appropriate Node if it already exists.

        Args:
            listener (Listener): Listener to add to the tree.
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

    def find_listeners(self, event: str) -> list[Listener]:
        """
        Get all listener functions from the nodes that match the provided event.

        Args:
            event (str): Event to match against.

        Returns:
            list[Listener]: List of all listeners that should be invoked for the provided event.
        """
        listeners = sum((node.listeners for node in self.find_nodes(event)), [])
        return listeners
