import unittest
from datetime import timedelta
from multiprocessing import Event as MultiprocessingEvent
from threading import Thread
from time import sleep
from unittest.mock import patch

from event_manager import EventModel
from event_manager.listeners.scheduled import ScheduledListener, run
from event_manager.listeners.simple import Listener


class DummyEvent(EventModel):
    __event_name__ = "dummy"


class TestListeners(unittest.TestCase):
    def test_listener_returns_future_with_result(self):
        result = []

        def handle(event):
            result.append(event.__event_name__)
            return "ok"

        listener = Listener(handle)
        future = listener(DummyEvent())

        self.assertEqual("ok", future.result(timeout=5))
        self.assertEqual(["dummy"], result)

    def test_scheduled_listener_stop_sets_event(self):
        listener = ScheduledListener(interval=timedelta(seconds=1), func=lambda: None)

        self.assertFalse(listener.sync_event.is_set())
        listener.stop()
        self.assertTrue(listener.sync_event.is_set())

    def test_run_executes_callback_until_event_is_set(self):
        called = []
        stop_event = MultiprocessingEvent()

        def callback():
            called.append(True)

        runner = Thread(target=run, args=(timedelta(milliseconds=10), callback, stop_event))
        runner.daemon = True
        runner.start()

        sleep(0.05)
        stop_event.set()
        runner.join(timeout=1)

        self.assertGreaterEqual(len(called), 1)

    def test_scheduled_listener_call_spawns_process(self):
        """Covers scheduled.py lines 52-60: ScheduledListener.__call__ starts a daemon process."""

        def task():
            return None

        listener = ScheduledListener(interval=timedelta(seconds=100), func=task)

        with patch("event_manager.listeners.scheduled.Process") as process_cls:
            listener()

        process_cls.assert_called_once()
        _, kwargs = process_cls.call_args
        self.assertIs(kwargs["target"], run)
        self.assertTrue(kwargs["daemon"])
        self.assertEqual(listener.interval, kwargs["kwargs"]["_interval"])
        self.assertIs(listener.func, kwargs["kwargs"]["_func"])
        self.assertIs(listener.sync_event, kwargs["kwargs"]["_event"])
        process_cls.return_value.start.assert_called_once_with()
