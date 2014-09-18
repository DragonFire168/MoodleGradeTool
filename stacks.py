__author__ = 'phillip'

import collections


class StackingList(list):
    """
    This list will also sort its contacts in to stacks (groups) based on the value of an attribute.
    The attribute must be usable as a dictionary key.
    """

    def __init__(self, attr, l=None):
        super(self, StackingList).__init__(l)
        self.attr = attr

    def update(self, obj=None):
        attr = self.attr
        if obj is None:
            self.stacks = {}
            for o in self:
                self._additmtostacks(o)
            return
        else:
            if not obj in self:
                raise ValueError("{} is not in {}".format(repr(obj), repr(self)))
            for l in self.stacks.itervalues():
                if obj in l:
                    l.remove(obj)
            self._additmtostacks(obj)


    def _additmtostacks(self, v):
        atrib = getattr(v, self.attr)
        if callable(atrib): atrib = atrib()
        self.stacks.setdefault(atrib, []).append(v)

    def __setitem__(self, key, value):
        if self[key] is value:
            self.update(value)
            return
        old = self[key]
        for l in self.stacks.itervalues():
            if old in l:
                l.remove(old)
        self._additmtostacks(value)

    def __setslice__(self, i, j, sequence):
        super(self, StackingList).__setslice__(i, j, sequence)
        self.update()

    def append(self, p_object):
        super(self, StackingList).append(p_object)
        self.update(p_object)

    def extend(self, iterable):
        for obj in iterable:
            self.append(obj)

    def __repr__(self):
        return "StackingList({s.attr}, {l})".format(s=self,l=super(self, StackingList).__repr__())