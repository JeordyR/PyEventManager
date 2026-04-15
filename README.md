# PyEventManager

[Read the Docs!](https://jeordyr.github.io/PyEventManager/)

PyEventManager is a simple event-based routing package allowing code to be structured in a pseudo-decentralized manner.

Instead of calling functions directly, you can emit an event and have one or more functions (listeners) configured to listen on that event execute. These listeners can currently be run either in a new thread or a new process, allowing the creation of background tasks for long-running jobs off an API event, for example.

Wrapped listeners return a [Future](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Future) that can be waited on to recieve the response(s) back from the listener.

There are multiple execution options when registering a listener:

* **Simple**: Execute the function (listener) when the specified event is emitted. Execution will occur in a new thread.
* **Batch**: Batch up the data from mulitple event emissions until one of the conditions is met, then execute the function with all of the received data. Execution and batching will occur in a new thread.
* **Scheduled**: Run a function on an interval with no inputs. Execution occurs in a new process.

---

## Todo

* Add tests
* Add support for external data stores (redis, rabbitmq?, etc.) for persistence of event data / batching


---

## Installation

Install via [pip](https://pypi.python.org/pypi/pyeventmanager)

`pip install pyeventmanager`

---

## Usage

### Events
```python
    from event_manager import EventModel

    class MyEvent(EventModel):
        __event_name__ = "somecategory.event"
        stuff: str
```

### Simple Listener

```python
    from event_manager import EventManager

    # Register a function to handle a specific event by name
    @EventManager.on(event="somecategory.event")
    def handle_some_event(data: MyDataType):
        ...

    # Register a function to handle a specific event by model
    @EventManager.on(event=MyEvent)
    def handle_some_event_model(data: MyEvent):
        ...

    # Register a function to handle all events in the system
    @EventManager.on(event="*")
    def handle_all_events(data: Any):
        ...

    # Register a function to handle all events for a category using wildcard
    @EventManager.on(event="somecategory.*")
    def handle_all_somecategory_events(data: Any):
        ...


    # Emit an event
    EventManager.emit(MyEvent(...))

    # Emit an event, wait for jobs to finish, and get the results
    from concurrent.futures import wait

    futures = EventManager.emit(MyEvent(...))
    wait(futures)

    results = [f.result() for f in futures]
```


### Batch Listener

```python
    from event_manager import EventManager

    # Batch all data for `MyEvent` until no new events occur for 60 seconds
    @EventManager.on_batch(event=MyEvent, batch_idle_window=60)
    def handle_some_event_batch(data: list[MyEvent]):
        ...

    # Batch data until 30 seconds pass, or 20 events come through, whichever happends first
    @EventManager.on_batch(event=MyEvent, batch_count=20, batch_window=30)
    def handle_some_event_batch(data: list[MyEvent]):
        ...

    # Batch all data for `MyEvent` and `MySecondEvent` until no new events occur for 60 seconds
    @EventManager.on_batch(event=[MyEvent, MySecondEvent], batch_idle_window=60)
    def handle_some_event_batch(data: list[MyEvent|MySecondEvent]):
        ...
```

### Scheduled Listener

Interval is defined using a [datetime.timedelta](https://docs.python.org/3/library/datetime.html#timedelta-objects) object.

```python
    from datetime import timedelta

    from event_manager import EventManager

    # Schedule a function to be run daily
    @EventManager.schedule(interval=timedelta(days=1))
    def run_daily():
        ...

    # Schedule a function to be run hourly
    @EventManager.schedule(interval=timedelta(hours=1))
    def run_hourly():
        ...
```

---

## API Documentation