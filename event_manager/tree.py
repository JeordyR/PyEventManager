import collections
import fnmatch
from typing import Any


class Node:
    @staticmethod
    def str_is_pattern(s: str) -> bool:
        """
        Check if the provided string is a pattern or not.

        Args:
            s (str): String to check for pattern contents.

        Returns:
            bool: If the string is a patter or not
        """
        return "*" in s or "?" in s

    def __init__(self, name: str):
        """
        A node in the tree representing a name and the data linked to it.

        Args:
            name (str): Name of the node
        """
        self.name: str = name
        self.parent: "Node | Tree | None" = None
        self.children: collections.OrderedDict[str, "Node"] = collections.OrderedDict()
        self.data: list[Any] = []

    def add_child(self, node: "Node") -> "Node":
        """
        Add a child to the node.

        If an existing child already exists with the same name, will add the data from the provided node to
        the existing one.

        Args:
            node (Node): Child Node to add

        Returns:
            Node: Returns the node added as a child or the existing node that was extended.
        """
        # Merge data when existing node with same name is present
        if node.name in self.children:
            _node = self.children[node.name]

            for data in node.data:
                _node.add_data(name=_node.name, data=data)

            return _node
        # Add it and set its parent
        else:
            self.children[node.name] = node
            node.parent = self
            return node

    def add_data(self, name: str, data: Any):
        """
        Add data to this node.

        Args:
            listener (BaseListener): Listener to add to the node
        """
        if data not in self.data:
            self.data.append(data)

    def check_name(self, pattern: str) -> bool:
        """
        Check if the name of this node matches the provided pattern.

        Args:
            pattern (str): Pattern to match the name against.

        Returns:
            bool: Whether the name matched the pattern.
        """
        if self.str_is_pattern(pattern):
            return fnmatch.fnmatch(self.name, pattern)
        elif self.str_is_pattern(self.name):
            return fnmatch.fnmatch(pattern, self.name)
        else:
            return self.name == pattern

    def find_nodes(self, name: str | list[str] | tuple[str]) -> list["Node"]:
        """
        Get all nodes, including children, that match the provided name.

        Name can come in as a string, ie `some.name.withsub` or split into a list or tuple.

        Returns:
            list["Node"]: List of nodes that match the name.
        """
        # trivial case
        if not name:
            return []

        # parse name
        if isinstance(name, list | tuple):
            pattern, sub_patterns = name[0], name[1:]
        else:
            pattern, *sub_patterns = name.split(".")

        # first make sure that pattern matches _this_ name
        if not self.check_name(pattern):
            return []

        # when there are no sub patterns, return this one
        if not sub_patterns:
            return [self]

        # recursively match sub names with nodes
        return sum((node.find_nodes(name=sub_patterns) for node in self.children.values()), [self])


class Tree:
    def __init__(self):
        """
        A tree storing Nodes for mapping names to data.
        """
        self.children: collections.OrderedDict[str, Node] = collections.OrderedDict()

    def find_nodes(self, name: str | list[str] | tuple[str]) -> list[Node]:
        """
        Get all nodes that match the provided name.

        Name can come in as a string, ie `some.name.withsub` or split into a list or tuple.

        Returns:
            list["Node"]: List of nodes that match the name.
        """
        return sum((node.find_nodes(name=name) for node in self.children.values()), [])

    def add_data(self, name: str, data: Any) -> None:
        """
        Add a data point to the tree. Either add a new Node to the tree or add the data into
        the tree at the appropriate Node if it already exists.

        Args:
            name (str): Name of the node to add the data to.
            data (Any): Data to add to the tree.
        """
        # add nodes without evaluating wildcards, this is done during node lookup only
        names = name.split(".")
        _name = names[0]

        # lookup the deepest existing parent
        node = self
        while names:
            _name = names.pop(0)
            if _name in node.children:
                node = node.children[_name]
            else:
                new_node = Node(name=_name)
                node.add_child(new_node)
                node = new_node

        # add the data
        node.add_data(name=_name, data=data)

    def add_child(self, node: Node) -> Node:
        """
        Add a child Node directly to the tree. If a node with the same name already exists, the data from the
        provided Node will be merged into the existing.

        Args:
            node (Node): Node to add to the tree.

        Returns:
            Node: Node added to the tree, or the existing Node that was extended.
        """
        # Merge data when existing node with same name is present
        if node.name in self.children:
            _node = self.children[node.name]
            _node.data.extend(node.data)
            return _node
        # Add it and set its parent
        else:
            self.children[node.name] = node
            node.parent = self
            return node

    def find_data(self, name: str) -> list[Any]:
        """
        Get all data entries from the nodes that match the provided name.

        Args:
            name (str): Name to match against.

        Returns:
            list[Any]: List of all data items that match the provided name.
        """
        return sum((node.data for node in self.find_nodes(name)), [])
