__all__ = ["Referenced"]


class Referenced:
    """
    Tracks references to items (typically strings) and their associated types and tags.

    Attributes:
        items (dict): Maps item values to a dict with keys 'value', 'count', and 'tag'.
        types (dict): Maps type names to a dict with keys 'value' and 'count'.
    """

    def __init__(self):
        """
        Initialize a new Referenced tracker with empty items and types.
        """
        self.items: dict[str, dict] = {}
        self.types: dict[str, dict] = {}

    def new(self) -> None:
        """
        Reset the tracker, clearing all items and types.
        """
        self.__init__()

    def add(self, item: str, locationtype: str = None, tag=None) -> None:
        """
        Add an item to the tracker, incrementing its count if it already exists.
        Optionally track a type and a tag.

        Args:
            item (str): The item to add.
            locationtype (str, optional): The type/category of the item.
            tag (optional): An associated tag or identifier.
        """
        if item in self.items:
            self.items[item]["count"] += 1
            self.items[item]["tag"] = tag
        else:
            self.items[item] = {"value": item, "count": 1, "tag": tag}
        if locationtype:
            if locationtype in self.types:
                self.types[locationtype]["count"] += 1
            else:
                self.types[locationtype] = {"value": locationtype, "count": 1}

    def exists(self, item: str) -> bool:
        """
        Check if an item exists in the tracker.

        Args:
            item (str): The item to check.

        Returns:
            bool: True if the item exists, False otherwise.
        """
        return item in self.items

    def item(self, item: str) -> dict:
        """
        Get the dictionary entry for an item.

        Args:
            item (str): The item to retrieve.

        Returns:
            dict: The item's dictionary entry.
        """
        return self.items[item]

    def gettag(self, item: str):
        """
        Get the tag associated with an item.

        Args:
            item (str): The item to query.

        Returns:
            The tag value associated with the item.
        """
        return self.items[item]["tag"]

    def getcount(self, item: str) -> int:
        """
        Get the count of how many times an item has been added.

        Args:
            item (str): The item to query.

        Returns:
            int: The count of the item, or 0 if not present.
        """
        if item in self.items:
            return self.items[item]["count"]
        else:
            return 0

    def __str__(self) -> str:
        """
        Return a string representation of the tracked items and their counts.

        Returns:
            str: A string listing all items and their counts.
        """
        items_str = ", ".join([f"{v['value']} ({v['count']}x)" for v in self.items.values()])
        return f"[{items_str}]"

    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.

        Returns:
            str: The representation of the Referenced object.
        """
        return f"Referenced({self.items})"

    def __len__(self) -> int:
        """
        Return the number of unique items tracked.

        Returns:
            int: The number of items.
        """
        return len(self.items)
