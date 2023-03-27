__all__ = ['Referenced']

############################################################################################
#
#   This class has an instance variable items which is a dictionary that stores the items added to the list as keys and their count as values. 
#   The add function first converts the input string to lower case and checks if it already exists in the dictionary. 
#   If it does, it increments the count of that item. Otherwise, it adds a new entry to the dictionary with a count of 1. 
#   The exists function checks if an item exists in the dictionary, also in a case-insensitive way. 
#   The getcount function returns the count of an item in the dictionary, or 0 if it does not exist. 
#   The new function resets the items dictionary to an empty dictionary, effectively starting the list over
#
#
    
class Referenced:
    """referenced keeps track of a list of strings """

    def __init__(self):
        self.items = {}
        self.types = {}
    
    def new(self):
        self.__init__()
    
    def add(self, item, type = None):
        if item in self.items:
            self.items[item]["count"] += 1
        else:
            self.items[item] = {"value": item, "count": 1}
        if type:
            if type in self.types:
                self.types[type]["count"] += 1
            else:
                self.types[type] = {"value": type, "count": 1}
    
    def exists(self, item):
        return item in self.items
    
    def getcount(self, item):
        if item in self.items:
            return self.items[item]["count"]
        else:
            return 0
    
    def __str__(self):
        items_str = ", ".join([f"{v['value']} ({v['count']}x)" for v in self.items.values()])
        return f"[{items_str}]"
    
    def __repr__(self):
        return f"Referenced({self.items})"
