import unittest

from event_manager import EventModel
from event_manager.listeners.simple import Listener
from event_manager.tree import Node, Tree


class DummyEvent(EventModel):
    __event_name__ = "dummy"


class TestTree(unittest.TestCase):
    def test_add_listener_and_find_listeners_exact(self):
        tree = Tree()

        def callback(event):
            return event.__event_name__

        listener = Listener(callback)
        tree.add_listener("dummy", listener)

        listeners = tree.find_listeners("dummy")

        self.assertEqual(1, len(listeners))
        self.assertIs(listeners[0], listener)

    def test_find_listeners_supports_wildcards(self):
        tree = Tree()

        def callback(event):
            return event.__event_name__

        listener = Listener(callback)
        tree.add_listener("foo.*", listener)

        listeners = tree.find_listeners("foo.bar")

        self.assertEqual(1, len(listeners))
        self.assertIs(listeners[0], listener)

    def test_find_listeners_with_wildcard_query(self):
        """Covers Node.check_name line 82: query is the pattern, node name is a literal."""
        tree = Tree()

        def callback(event):
            return event.__event_name__

        listener = Listener(callback)
        tree.add_listener("foo.bar", listener)

        listeners = tree.find_listeners("foo.*")

        self.assertEqual(1, len(listeners))
        self.assertIs(listeners[0], listener)

    def test_find_listeners_empty_name_returns_empty(self):
        """Covers Node.find_nodes line 99: trivial empty-name case."""
        tree = Tree()

        def callback(event):
            return event.__event_name__

        tree.add_listener("dummy", Listener(callback))

        result = tree.find_listeners("")

        self.assertEqual([], result)

    def test_tree_add_listener_reuses_existing_parent_node(self):
        """Covers Tree.add_listener line 155: path segment already exists in tree."""
        tree = Tree()

        def cb1(event):
            pass

        def cb2(event):
            pass

        listener1 = Listener(cb1)
        listener2 = Listener(cb2)

        tree.add_listener("foo.bar", listener1)
        # "foo" already exists — add_listener must traverse into it (line 155)
        tree.add_listener("foo.baz", listener2)

        self.assertEqual(1, len(tree.find_listeners("foo.bar")))
        self.assertEqual(1, len(tree.find_listeners("foo.baz")))

    def test_node_add_child_merges_existing_node(self):
        """Covers Node.add_child lines 48-53: merging when child with same name exists."""
        parent = Node("root")

        child1 = Node("child")
        listener1 = Listener(lambda e: None)
        child1.listeners = [listener1]
        parent.add_child(child1)

        child2 = Node("child")
        listener2 = Listener(lambda e: None)
        child2.listeners = [listener2]
        returned = parent.add_child(child2)  # triggers merge path

        self.assertIs(returned, child1)
        self.assertIn(listener1, parent.children["child"].listeners)
        self.assertIn(listener2, parent.children["child"].listeners)

    def test_node_add_listener_deduplicates(self):
        """Covers Node.add_listener line 68->exit: duplicate listener is silently ignored."""
        node = Node("foo")
        listener = Listener(lambda e: None)

        node.add_listener("foo", listener)
        node.add_listener("foo", listener)  # duplicate — should be a no-op

        self.assertEqual(1, len(node.listeners))

    def test_tree_add_child_merges_existing_node(self):
        """Covers Tree.add_child lines 177-179: merging when top-level node already exists."""
        tree = Tree()
        listener1 = Listener(lambda e: None)
        listener2 = Listener(lambda e: None)

        node1 = Node("root")
        node1.listeners = [listener1]
        tree.add_child(node1)

        node2 = Node("root")
        node2.listeners = [listener2]
        returned = tree.add_child(node2)  # triggers merge path

        self.assertIs(returned, node1)
        self.assertIn(listener1, tree.children["root"].listeners)
        self.assertIn(listener2, tree.children["root"].listeners)
