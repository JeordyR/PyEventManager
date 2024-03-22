"""
.. include:: ../README.md
"""

__all__ = ["EventManager", "ForkType", "QueueInterface", "ProcessQueue", "ThreadQueue"]
from .event_manager import EventManager
from .fork_types import ForkType
from .queues.base import QueueInterface
from .queues.memory import ProcessQueue, ThreadQueue
