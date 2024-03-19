"""
.. include:: ../README.md
"""

__all__ = ["EventManager", "QueueInterface", "ProcessQueue", "ThreadQueue"]
from .event_manager import EventManager
from .queues.base import QueueInterface
from .queues.memory import ProcessQueue, ThreadQueue
