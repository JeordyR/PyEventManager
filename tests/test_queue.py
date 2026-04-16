import unittest

from event_manager import EventModel
from event_manager.queues.memory import ThreadQueue


class DummyEvent(EventModel):
    __event_name__ = "dummy"


class TestThreadQueue(unittest.TestCase):
    def test_put_updates_last_updated_and_get_all_returns_events(self):
        queue = ThreadQueue()

        self.assertIsNone(queue.last_updated)
        queue.put(DummyEvent())
        self.assertEqual(1, len(queue))
        self.assertIsNotNone(queue.last_updated)

        items = queue.get_all()

        self.assertEqual(1, len(items))
        self.assertEqual("dummy", items[0].__event_name__)
        self.assertEqual(0, len(queue))
        self.assertIsNone(queue.last_updated)
