# #########################################################################
# Author:      Cory Nance
# Author:      Phillip Wall
# Description: Script to grade labs   									 
# Date: 	   20 August 2014											 
# Assumptions: Submissions were mass-downloaded from Moodle and unzipped.
##########################################################################

import os
import sys
import shutil
import zipfile
from threading import Thread
from Queue import Queue

import argparse

import moodlegradetool.cliforms as cliforms
from moodlegradetool.filemanager import prepare_directory
import moodlegradetool.student as student
from moodlegradetool.reporting import XMLReport
from moodlegradetool.testing import tests, findtests, loadtesterplugins

MAX_BUILDS = 5

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # Force unbuffered stdout

def main():

    loadtesterplugins()  # Load the tester plugins

    parser = argparse.ArgumentParser(description="Compile, test, and grade Java files submitted via Moodle.")
    parser.add_argument('-p', '--path', metavar='FolderPath', type=str, help='Path to a zip file or folder containing '
                                                                             'the Moodle submissions.')
    parser.add_argument('-c', '--config', metavar='ConfigPath', type=str, help='Path to the configuration directory.')
    parser.add_argument('-q', '--quick', action='store_true', help='Quick run.  After selecting tests the program will run the tests, save '
                                              'the results, and terminate.')
    args = parser.parse_args()
    
    #set path and config variables
    path = os.path.abspath(args.path) if args.path else None
    config = os.path.abspath(args.config) if args.config else None
    quick = args.quick

    paths = {'folder': path, 'config': config}
    
    if path is None or config is None:
        paths = fileconfig(**paths)

    for k, v in paths.iteritems():
        paths[k] = os.path.abspath(v)
  
    path = paths['folder']
    # Fixed comparison to leverage negative indexes -Phillip Wall
    if '.zip' == path[-4:]:
        if os.path.exists(path[:-4]):
            shutil.rmtree(path[:-4])
        os.mkdir(path[:-4])

        with zipfile.ZipFile(path) as z:
            z.extractall(path=path[:-4])  # Extract the files

        path = path[:-4]  # Set path to newly created directory
    paths['folder'] = path

    if '.zip' == paths['config'][-4:]:
        paths['config'] = paths['config'][:-4]

    os.chdir(paths['config'])  # Change the working directory to the test configuration directory

    findtests(paths['config'])

    os.chdir(paths['folder'])  # Change to the grading directory

    tkeys = select_test()  # Run the TestSelector form
    if tkeys:  # If we selected tests
        tlist = [tests[key] for key in tkeys]  # Get the test classes
    else:
        tlist = [tests['Manual']]  # Else we need a list of just the Manual test

    student.Student.tests = tlist  # Set the default tests for the student class
    students = prepare_directory(path)  # Prepare the grading directory

    q = Queue(maxsize=MAX_BUILDS)  # Set up the build queue

    t = Thread(target=do_builds, args=(students, q))  # Set up the building thread
    t.start()

    #Keep going while the thread is alive or while there are still programs to be worked
    while t.isAlive() or not q.empty():
        #Get the next student in the list
        currentstudent = q.get()
        assert isinstance(currentstudent, student.Student)

        #Print out the information
        print "#" * 35, '\n'
        print currentstudent.name
        print "{path}/{student.name}/{student.java_class}.java".format(path=path, student=currentstudent)

        #Make sure we're in the right state before we continue
        if currentstudent.state == student.StudentState.building:
            print "Waiting for build to finish..."
            currentstudent.proc.wait()

        if currentstudent.state == student.StudentState.build_error:
            print "There was a problem during build, check the build.log in the students folder."
            continue

        #Change the working path to the student's directory
        wrkpath = "{}/{}".format(path, currentstudent.name)

        print "Running tests..."
        currentstudent.dotests()  # Run all the tests

        #Print the results
        for test in currentstudent.tests:
            print "\nThe program got a score of {test.score}/{test.possible} on {test.name}".format(test=test)

        print "Program got a total score of {s.score}/{s.possible}".format(s=currentstudent)

        if quick:
            continue

        #Show the results for the student, and get the form options
        save, manual = process_tests(currentstudent)

        #If save was selected on the form we want to save the output of the test
        if save:
            for test in filter(lambda t: hasattr(t,'output'), currentstudent.tests):
                with open("{path}/{test}_output.log".format(path=wrkpath, test=test.name), 'w') as log:
                    log.write(test.output())

        #If manual was selected we want to manually interact with the program
        if manual:
            ans = 'y'
            while ans and ans.lower()[0] == 'y':  # Continue while the user keeps pressing yes
                print
                currentstudent.dotest(tests['Manual'])
                ans = raw_input("Program finished, do you want to rerun it? (y/n)")
                print

    os.chdir(path)
    t.join()

    #Save report
    XMLReport(students).save('results.xml')

@cliforms.forms
def fileconfig(stdscr, folder="", config="", *args):
    """
    Displays a file selection dialog.
    :param folder: The grading folder to default to
    :param config: The test configuration folder
    :returns: A dictionary containing the folder and config dirs
    :rtype: dict
    """
    f = cliforms.FileDialog(folder, config)
    f.edit()

    #Setup the dict
    ret = {'folder': f.directory.value, 'config': f.testconf.value}

    #Setup the default for the folder
    if not ret['folder']:
        ret['folder'] = os.curdir

    #Setup the default for the test configuration folder
    if not ret['config']:
        ret['config'] = ret['folder']

    return ret

@cliforms.forms
def select_test(*args):
    """Will prompt the user for the test they want to run.
    :returns: A list of keys of the selected tests or None if none selected
    :rtype : List
    """

    keys = tests.keys()  # Get the current tests
    f = cliforms.TestsSelector()
    f.edit()  # Call the test selector form
    indexes = f.selector.value  # Get the required values from the form

    if not indexes:
        return None  # If nothing has been selected we want to return None

    return [keys[i] for i in indexes]  # Otherwise get the keys and return them

@cliforms.forms
def process_tests(stdscr, student):
    """
    Processes the results of a test.
    :returns: A tuple of (Save output, Run Manual)
    :rtype: tuple
    """
    f = cliforms.StudentRecord(student=student)  # Create the form for this student
    f.edit()

    #Get the needed values from the form and return them
    return f.checksave.value, f.checkmanual.value


def do_builds(studentslist, que):
    """
    Performs the building of the source files for each student.
    :param studentslist: The list of students to build
    :param que: The que to put the students who are building on
    """
    for curstudent in studentslist:
        curstudent.dobuild()
        que.put(curstudent)


if __name__ == "__main__":
    main()
#end if
