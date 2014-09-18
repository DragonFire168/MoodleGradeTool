__author__ = 'phillip'
# Requires enum34 from python package index

import os
import subprocess
import datetime

from pydispatch import dispatcher
from enum import Enum

STATE_SIGNAL = "StudentStateChanged"

class StateError(Exception):
    pass


#Needs to be defined here so its ready when Student is being interpreted
def requirestate(state):
    """
    Decorator: Requires the object be in a certain state before the function can be run. An iterable can be passed
    in which case the objects state needs to match any of the elements.

    :param state: The state(s) that needs to be matched
    """
    def decorator(func):
        def checkstate(self, *args, **kwargs):
            try:
                try:
                    assert self.state in state
                except TypeError:
                    assert self.state == state
            except AssertionError as ex:
                raise StateError("{obj} is not in {state} state(s)".format(obj=repr(self), state=str(state)))
            return func(self, *args, **kwargs)

        return checkstate

    return decorator


class StudentState(Enum):
    not_built = 0  # The program has not been built yet
    building = 1  # The program is in the process of building
    build_error = -1  # There was a problem during building
    not_tested = 2  # The program built ok, but has not been tested yet
    testing = 3  # The program is in the process of being tested
    ready = 4  # The program has been tested


class Student(object):
    tests = []

    def __init__(self, name, main_class, otherclasses=None):
        self.name = name
        self.java_class = main_class
        self.classlist = otherclasses if not otherclasses is None else []
        self.directory = os.path.abspath('./' + name)
        self.proc = None

        #Instansiate the test classes provided
        #We need to make sure that we don't modify the existing list
        testers = self.tests
        self.tests = []
        for t in testers:
            self.tests.append(t(name, main_class))

        self._state = StudentState.not_built  # Set the state

    @requirestate((StudentState.not_tested, StudentState.ready))
    def dotests(self):
        """Performs all the tests registered with this student."""

        self.state = StudentState.testing
        for test in self.tests:
            test.start()

        self.state = StudentState.ready

    @requirestate((StudentState.not_tested, StudentState.ready))
    def dotest(self, cls):
        """
        Performs a specific test. Adds the test to the students test list if not there already.
        :param cls: The test class to perform
        """
        t = None
        #Look in the tests list
        for test in self.tests:
            if isinstance(test, cls):  # See if any of them are instances of the passed class
                t = test  # If so use the test
        if not t:
            t = cls(self.name, self.java_class)  # If not instantiate it
            self.tests.append(t)  # And add it to tests
        t.start()  # Start it

    @requirestate(StudentState.not_built)
    def dobuild(self):
        """
        Builds the program.
        """
        self.state = StudentState.building  # Set state to building
        try:
            with open(self.directory + "/build.log", 'a') as log:  # Open the log file
                #Log entry header
                log.write('\n\n' + str(datetime.datetime.now()) + '\n')
                log.write("Starting build of %s.java\n\n" % self.java_class)

                #Start the build
                self.proc = subprocess.Popen(('javac', "/".join(self.java_class.split(".")) + ".java"),
                                             cwd=self.directory, stdout=log, stderr=subprocess.STDOUT)
        except Exception as ex:
            self.state = StudentState.build_error
            raise ex

    @property
    @requirestate(StudentState.ready)
    def score(self):
        """
        Calculates the students score
        :return: The total score of all the tests
        :rtype: int
        """
        return reduce(lambda scr, test: scr + test.score, self.tests, 0)

    @property
    def possible(self):
        """
        Calculates the students possible score
        :return: The total possible score for all the tests
        :rtype: int
        """
        return reduce(lambda scr, test: scr + test.possible, self.tests, 0)

    @property
    def state(self):
        """
        The state the student object is in.

        :rtype: StudentState
        """
        # If the state is building we need to check to see if there was a build error
        if self._state == StudentState.building and self.proc and not self.proc.poll() is None:
            if self.proc.returncode == 0:
                self.state = StudentState.not_tested  # Set state to not tested when build succeeds
            else:
                self.state = StudentState.build_error

        return self._state

    @state.setter
    def state(self, value):
        assert isinstance(value, StudentState)
        self._state = value
        dispatcher.send(signal=STATE_SIGNAL, sender=self)

    def __repr__(self):
        return "Student({}, {})".format(self.name, self.java_class)

    def __str__(self):
        return self.name + ": " + self.java_class
