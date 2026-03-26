"""
.. include:: ../README.md
"""

__all__ = ["EventManager", "QueueInterface", "ProcessQueue", "EventModel"]
from .manager import EventManager
from .models import EventModel
from .queues.base import QueueInterface
from .queues.memory import ProcessQueue
