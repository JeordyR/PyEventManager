from datetime import datetime, timedelta
from unittest.mock import patch

from event_manager import EventManager, EventModel
from event_manager.listeners.batch import batch_input
from event_manager.queues.memory import ThreadQueue
from event_manager.tree import Tree


class FirstEvent(EventModel):
    __event_name__ = "first"


class SecondEvent(EventModel):
    __event_name__ = "second"


class _Ev(EventModel):
    __event_name__ = "ev"


def test_on_batch_shared_listener_batches_multiple_event_types():
    EventManager._event_tree = Tree()

    observed_events: list[EventModel] = []

    @EventManager.on_batch(event=[FirstEvent, SecondEvent], batch_window=1)
    def collect_events(events: list[EventModel]) -> int:
        observed_events.extend(events)
        return len(events)

    first_futures = EventManager.emit(FirstEvent())
    second_futures = EventManager.emit(SecondEvent())

    assert len(first_futures) == 1
    assert len(second_futures) == 1
    assert first_futures[0] is second_futures[0]

    result = first_futures[0].result(timeout=5)

    assert result == 2
    assert {event.__event_name__ for event in observed_events} == {"first", "second"}


def test_batch_input_idle_window_logs_when_updated_too_recently():
    """Covers batch.py line 55: the else branch when data was updated too recently."""
    queue = ThreadQueue()
    queue.put(_Ev())

    base_time = datetime(2024, 1, 1, 12, 0, 0)
    queue.last_updated = base_time  # override to a controlled timestamp

    call_count = [0]

    def mock_now():
        call_count[0] += 1
        if call_count[0] == 1:
            # First check: since_last = 0 seconds → too recent → hits line 55
            return base_time
        # Second check: since_last = 3 seconds → ≥ batch_idle_window=2 → break
        return base_time + timedelta(seconds=3)

    results = []

    def callback(events):
        results.extend(events)
        return len(events)

    with patch("event_manager.listeners.batch.time.sleep"):
        with patch("event_manager.listeners.batch.datetime") as mock_dt:
            mock_dt.now = mock_now
            batch_input(0, 2, 0, queue, callback)

    assert len(results) == 1


def test_batch_input_loops_until_batch_window_expires():
    """Covers batch.py branch 58->39: loop continues when batch_window hasn't elapsed yet."""
    queue = ThreadQueue()
    queue.put(_Ev())

    results = []

    def callback(events):
        results.extend(events)
        return len(events)

    # batch_window=2 with sleep mocked:
    # iteration 1: elapsed=1, 2 > 1 → branch 58->39 (loop back)
    # iteration 2: elapsed=2, 2 <= 2 → break
    with patch("event_manager.listeners.batch.time.sleep"):
        batch_input(0, 0, 2, queue, callback)

    assert len(results) == 1
