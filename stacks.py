__author__ = 'phillip'

import collections


class StackingList(list):
    """
    This list will also sort its contacts in to stacks (groups) based on the value of an attribute.
    The attribute must be usable as a dictionary key.
    """

    def __init__(self, attr, l=None):
        """
        Initializes a StackingList
        :param attr: The attribute to group by
        :param l: Any thing that can initialize the built-in list type
        """
        if l is None: l = ()
        super(StackingList, self).__init__(l)  # Initialize the list
        self.attr = attr  # Store the name of the attribute we're looking for
        self.update()  # Update the stacks

    def update(self, obj=None):
        attr = self.attr  # Copy to local storage for quicker access
        if obj is None:  # See if we should do a whole list update
            self.stacks = collections.defaultdict(list)  # The dictionary for the stacks
            for o in self:  # For every object we contain
                self._additmtostacks(o)  # Add it to the stacks
        else:
            if not obj in self:  # We're only interested in objects we contain
                raise ValueError("{} is not in {}".format(repr(obj), repr(self)))
            #We need to remove the object from whatever stacks its currently in
            for l in self.stacks.itervalues():
                if obj in l:
                    l.remove(obj)
            #And then re-add it to the stacks
            self._additmtostacks(obj)


    def _additmtostacks(self, v):
        atrib = getattr(v, self.attr)  # Get the attribute from the item
        if callable(atrib): atrib = atrib()  # If the attribute is callable, then call it and store the value
        self.stacks[atrib].append(v)  # Add the item to the appropriate stack

    def __setitem__(self, key, value):
        #If the item we're trying to set is the same as the value we're trying to set, we don't need to do anything
        if self[key] is value:
            return

        old = self[key]  # Get the old value
        for l in self.stacks.itervalues():
            if old in l:
                l.remove(old)  # And remove the value from the stacks
        super(StackingList, self).__setitem__(key, value)  # Set the item
        self.update(value)  # Add it to the stacks

    def __setslice__(self, i, j, sequence):
        super(StackingList, self).__setslice__(i, j, sequence)  # Set the slice
        self.update()  # Do a whole list update

    def append(self, p_object):
        super(StackingList, self).append(p_object)  # Append the object
        self.update(p_object)  # Do an update

    def pop(self, index=-1):
        ret = super(StackingList, self).pop(index)

        #Remove the returned value from the stacks
        for l in self.stacks.itervalues():
            if ret in l:
                l.remove(ret)
        return ret

    def remove(self, value):
        super(StackingList, self).remove(value)

        #Remove the returned value from the stacks
        for l in self.stacks.itervalues():
            if value in l:
                l.remove(value)

    def extend(self, iterable):
        for obj in iterable:
            self.append(obj)  # Do an update for each object

    def __repr__(self):
        return "StackingList({s.attr}, {l})".format(s=self,l=super(StackingList, self).__repr__())

    def __str__(self):
        ret = ""
        stacks = self.stacks  # Local variable access for speed and simplicity
        for k in stacks:
            l = [str(i) for i in stacks[k]]  # Get a list of every item in the stack as a string
            ret += "%s: %s\n" % (str(k), str(l))  # And a append a line for this stack
        return ret