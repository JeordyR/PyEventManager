# PyEventManager

[Read the Docs!](https://jeordyr.github.io/PyEventManager/)

PyEventManager is a simple event-based routing package allowing code to be structured in a pseudo-decentralized manner.

Instead of calling functions directly, you can emit an event and have one or more functions (listeners) configured to listen on that event execute. These listeners can currently be run either in a new thread or a new process, allowing the creation of background tasks for long-running jobs off an API event, for example.

There are multiple execution options when registering a listener:

* **Simple**: Execute the function (listener) when the specified event is emitted.
* **Batch**: Batch up the data from mulitple event emissions until no new events occur for `interval` seconds, then execute the function with all of the received data.
* **Scheduled**: Run a function on an interval with no inputs.

For each listener type, there are multiple execution options determining how the function will be executed; determined by `fork_type`

* **Process(Default)**: The listener is run in a new Process
* **Thread**: The listener is run in a new Thread

---

## Todo

* Add tests
* Add support for async execution within an existing event loop
* Add support for external data stores (redis, rabbitmq?, etc.) for persistence of event data / batching
* ~~Fix up docstrings across the board~~
* ~~Consider adding support for returning data from the listeners~~ (emit now returns a list of Futures that caller can wait on and get results from if they want)

---

## Installation

Install via [pip](https://pypi.python.org/pypi/pyeventmanager)

`pip install pyeventmanager`

---

## Usage

### Simple Listener

.. code-block:: python
    from event_manager import EventManager

    em = EventManager()

    # Use a decorator to register a simple listener

    @em.on(event="somecategory.event")
    def handle_some_event(data: MyDataType):
        ...

    # Register a function to handle all events in the system
    @em.on_all()
    def handle_all_events(data: Any):
        ...

    # Register a function to handle all events for a category using wildcard
    @em.on(event="somecategory.*")
    def handle_all_somecategory_events(data: Any):
        ...

    # Register a simple listener using callback syntax

    def also_handle_some_event(data: MyDataType):
        ...

    em.on(event="somecategory.event", func=also_handle_some_event)

    # Emit an event without worrying about response
    em.emit(event="somecategory.event", data=MyDataType(...))

    # Emit an event, wait for jobs to finish, and get the results
    from concurrent.futures import wait

    futures = em.emit(event="somecategory.event, data=MyDataType(...))
    wait(futures)

    results = [f.result() for f in futures]


### Simple Listener With Threading

.. code-block:: python
    from event_manager import EventManager, ForkType

    em = EventManager()

    # Use Threading instead of Processing
    @em.on(event="something.*", fork_type=ForkType.THREAD)

### Batch Listener

.. code-block:: python
    from event_manager import EventManager, ForkType, ThreadQueue

    em = EventManager()

    # Batch all data for `category.some_event` until no new events occur for 60 seconds
    @em.on(event="category.some_event", batch=True, batch_window=60)
    def handle_some_event_batch(data: list[MyDataType]):
        ...

    # Same batch, using Threading.
    # The queue type will be auto-detected if not specified, but better to be explicit.
    @em.on(
        event="category.some_event",
        fork_type=ForkType.THREAD,
        batch=True,
        batch_window=60,
        queue_type=ThreadQueue,
    )
    def handle_some_event_batch(data: list[MyDataType]):
        ...

### Scheduled Listener

Interval is defined using a [datetime.timedelta](https://docs.python.org/3/library/datetime.html#timedelta-objects) object.

.. code-block:: python
    from datetime import timedelta

    from event_manager import EventManager

    em = EventManager()

    # Schedule a function to be run daily
    @em.schedule(interval=timedelta(days=1))
    def run_daily():
        ...

    # Schedule a function to be run hourly
    @em.schedule(interval=timedelta(hours=1))
    def run_hourly():
        ...

### Using A Custom Queue for Batch Listener

.. code-block:: python
    from datetime import datetime
    from typing import Any

    from event_manager import EventManager, ForkType, QueueInterface

    class MyCustomQueue(QueueInterface):
        last_updated: datetime | None

        def __init__(self, ...):
            self.last_updated = None

        def __len__(self):
            length = 0
            ...
            return length

        def empty(self) -> bool:
            # Check if the queue is empty
            num_items = 0
            ...
            if num_items > 0:
                return False

            return True

        def get(self) -> Any:
            # Get an item from the queue
            item = {}
            ...
            return item

        def get_all(self) -> list[Any]:
            # Get all items from the queue
            items = []
            ...
            return items

        def put(self, item: Any):
            # Put item to queue
            ...

    em = EventManager()

    # Add a batched listener and pass in our custom Queue implementation
    @em.on(
        event="category.some_event",
        batch=True,
        batch_window=60,
        queue_type=MyCustomQueue,
    )
    def handle_batch_process(data: list[Any]):
        ...

    # Add a batched listener configured to use Threading with our custom Queue implementation
    @em.on(
        event="category.some_event",
        fork_type=ForkType.THREAD,
        batch=True,
        batch_window=60,
        queue_type=MyCustomQueue,
    )
    def handle_batch_process(data: list[Any]):
        ...
---

## API Documentation