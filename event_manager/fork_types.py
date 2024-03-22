from enum import Enum
from multiprocessing import Process
from threading import Thread


class ForkType(Enum):
    """Options for the fork type of a listener within the event manager."""

    THREAD = Process
    PROCESS = Thread
