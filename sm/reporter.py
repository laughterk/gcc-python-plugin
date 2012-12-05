#   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012 Red Hat, Inc.
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

from collections import namedtuple
import gccutils

class Note(namedtuple('Note', ('gccloc', 'msg'))):
    pass

class Report:
    def __init__(self, err, notes):
        self.err = err
        self.notes = notes

class Reporter:
    pass

class StderrReporter(Reporter):
    def __init__(self):
        self.curfun = None
        self.curfile = None

    def add(self, report):
        err = report.err
        gccloc = err.gccloc
        if err.function != self.curfun or gccloc.file != self.curfile:
            # Fake the function-based output
            # e.g.:
            #    "tests/sm/examples/malloc-checker/input.c: In function 'use_after_free':"
            import sys
            sys.stderr.write("%s: In function '%s':\n"
                             % (gccloc.file, err.function.decl.name))
            self.curfun = err.function
            self.curfile = gccloc.file
            import sys
        gccutils.error(report.err.gccloc, report.err.msg)
        self.curfun = err.function
        self.curfun = err.function

        for note in report.notes:
            gccutils.inform(note.gccloc, note.msg)