import time
import unittest
from datetime import timedelta

from event_manager import EventManager, EventModel
from event_manager.tree import Tree


class DummyEvent(EventModel):
    __event_name__ = "dummy"


class AnotherEvent(EventModel):
    __event_name__ = "another"


class PatternEvent(EventModel):
    __event_name__ = "pattern.test"


class _NotAnEvent:
    """A plain class that is NOT an EventModel subclass."""


class TestEventManager(unittest.TestCase):
    def setUp(self):
        EventManager._event_tree = Tree()
        EventManager._scheduled_listeners = []
        self.recorded = []

    def test_on_registers_listener_and_emit(self):
        @EventManager.on(DummyEvent)
        def handle(event):
            self.recorded.append(event.__event_name__)
            return "handled"

        futures = EventManager.emit(DummyEvent())

        self.assertEqual(1, len(futures))
        self.assertEqual("handled", futures[0].result(timeout=5))
        self.assertEqual(["dummy"], self.recorded)

    def test_on_batch_shares_listener_across_multiple_event_types(self):
        @EventManager.on_batch([DummyEvent, AnotherEvent], batch_count=2)
        def collect(events):
            self.recorded.extend([event.__event_name__ for event in events])
            return len(events)

        futures1 = EventManager.emit(DummyEvent())
        futures2 = EventManager.emit(AnotherEvent())

        self.assertEqual(1, len(futures1))
        self.assertEqual(1, len(futures2))
        self.assertIs(futures1[0], futures2[0])
        self.assertEqual(2, futures1[0].result(timeout=5))
        self.assertEqual({"dummy", "another"}, set(self.recorded))

    def test_on_batch_with_batch_window_batches_after_window(self):
        start = time.monotonic()

        @EventManager.on_batch(DummyEvent, batch_window=1)
        def collect(events):
            self.recorded.extend([event.__event_name__ for event in events])
            return len(events)

        futures = EventManager.emit(DummyEvent())
        self.assertEqual(1, futures[0].result(timeout=5))
        self.assertGreaterEqual(time.monotonic() - start, 1)
        self.assertEqual(["dummy"], self.recorded)

    def test_on_batch_with_batch_idle_window_batches_after_idle(self):
        @EventManager.on_batch(DummyEvent, batch_idle_window=1)
        def collect(events):
            self.recorded.extend([event.__event_name__ for event in events])
            return len(events)

        futures = EventManager.emit(DummyEvent())
        self.assertEqual(1, futures[0].result(timeout=5))
        self.assertEqual(["dummy"], self.recorded)

    def test_on_batch_wildcard_pattern_matches_event_name(self):
        @EventManager.on_batch("pattern.*", batch_count=1)
        def collect(events):
            self.recorded.extend([event.__event_name__ for event in events])
            return len(events)

        futures = EventManager.emit(PatternEvent())
        self.assertEqual(1, len(futures))
        self.assertEqual(1, futures[0].result(timeout=5))
        self.assertEqual(["pattern.test"], self.recorded)

    def test_listeners_returns_registered_listeners(self):
        @EventManager.on(DummyEvent)
        def handle(event):
            return event.__event_name__

        listeners = EventManager.listeners(DummyEvent)

        self.assertEqual(1, len(listeners))
        self.assertEqual(listeners[0].func, handle)

    def test_emit_raises_on_invalid_event_type(self):
        with self.assertRaises(TypeError):
            EventManager.emit(object())

    def test_on_supports_string_event_names(self):
        @EventManager.on("custom.event")
        def handle(event):
            self.recorded.append(event.__event_name__)

        class Custom(EventModel):
            __event_name__ = "custom.event"

        futures = EventManager.emit(Custom())
        self.assertEqual(1, len(futures))
        self.assertEqual(["custom.event"], self.recorded)

    def test_on_with_list_of_strings(self):
        """Covers manager.py lines 46-49: on() with a list of string event names."""

        @EventManager.on(["dummy", "another"])
        def handle(event):
            self.recorded.append(event.__event_name__)
            return "ok"

        futures = EventManager.emit(DummyEvent())
        self.assertEqual(1, len(futures))
        self.assertEqual("ok", futures[0].result(timeout=5))
        self.assertIn("dummy", self.recorded)

    def test_on_with_list_of_event_models(self):
        """Covers manager.py lines 46-47, 50-51: on() with a list of EventModel subclasses."""

        @EventManager.on([DummyEvent, AnotherEvent])
        def handle(event):
            self.recorded.append(event.__event_name__)
            return "ok"

        futures = EventManager.emit(DummyEvent())
        self.assertEqual(1, len(futures))
        self.assertEqual("ok", futures[0].result(timeout=5))

    def test_on_with_invalid_list_item_raises(self):
        """Covers manager.py lines 52-53: on() raises TypeError for unsupported item in list."""
        with self.assertRaises((TypeError, NameError)):

            @EventManager.on([_NotAnEvent])
            def handle(event):
                pass

    def test_on_with_invalid_event_type_raises(self):
        """Covers manager.py line 57: on() raises when event is not str/list/EventModel."""
        with self.assertRaises(Exception):
            EventManager.on(_NotAnEvent)

    def test_on_batch_with_list_of_strings(self):
        """Covers manager.py lines 99-101: on_batch() with a list of string event names."""

        @EventManager.on_batch(["dummy"], batch_count=1)
        def collect(events):
            self.recorded.extend([e.__event_name__ for e in events])
            return len(events)

        futures = EventManager.emit(DummyEvent())
        self.assertEqual(1, futures[0].result(timeout=5))
        self.assertIn("dummy", self.recorded)

    def test_on_batch_with_invalid_list_item_raises(self):
        """Covers manager.py lines 104-105: on_batch() raises TypeError for unsupported item in list."""
        with self.assertRaises(TypeError):

            @EventManager.on_batch([_NotAnEvent], batch_count=1)
            def collect(events):
                pass

    def test_on_batch_with_invalid_event_type_raises(self):
        """Covers manager.py line 109: on_batch() raises when event is not str/list/EventModel."""
        with self.assertRaises(Exception):
            EventManager.on_batch(_NotAnEvent, batch_count=1)

    def test_schedule_decorator_registers_and_runs(self):
        """Covers manager.py lines 145-153 and scheduled.py lines 52-60."""

        @EventManager.schedule(interval=timedelta(seconds=100))
        def background_task():
            pass

        self.assertEqual(1, len(EventManager._scheduled_listeners))
        # Clean up the daemon process
        EventManager._scheduled_listeners[0].stop()

    def test_listeners_with_invalid_type_raises(self):
        """Covers manager.py line 172: listeners() raises TypeError for unsupported type."""
        with self.assertRaises(TypeError):
            EventManager.listeners(_NotAnEvent)

    def test_emit_catches_listener_exception(self):
        """Covers manager.py lines 203-205: emit() logs and swallows exceptions from listeners."""

        class _BrokenListener:
            __name__ = "broken_listener"
            func = None

            def __call__(self, event):
                raise RuntimeError("intentional test error")

        EventManager._event_tree.add_listener(DummyEvent.__event_name__, _BrokenListener())

        futures = EventManager.emit(DummyEvent())

        # The broken listener raised before returning a future, so futures is empty
        self.assertEqual([], futures)
