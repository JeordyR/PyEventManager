from enum import Enum


class ForkType(Enum):
    """Options for the fork type of a listener within the event manager."""

    THREAD = 1
    PROCESS = 2
