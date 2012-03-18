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

import os
import shutil
from subprocess import Popen, PIPE, check_output
import sys

def indent(prefix, text):
    text = str(text)
    return '\n'.join([prefix + line
                      for line in text.splitlines()])

class ConfigurationFailure(Exception):
    pass

class CheckFor:
    """
    Context manager for wrapping a feature test
    The feature test should raise ConfigurationFailure to signify a failure
    """
    def __init__(self, initmsg, mandatory, okmsg=None, failmsg='failed'):
        self.initmsg = initmsg
        self.mandatory = mandatory
        self.okmsg = okmsg
        self.failmsg = failmsg
        self.result = None

    # context manager hooks:
    def __enter__(self):
        sys.stdout.write('%s... ' % self.initmsg) # no newline
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # exception occurred:
            self.result = False

            # is it one of ours, signifiying the failure of a test?
            if isinstance(exc_val, ConfigurationFailure):
                # Write the failure message:
                sys.stdout.write('%s\n' % self.failmsg)

                if self.mandatory:
                    # Print diagnostic information:
                    print(exc_val)

                    # terminate the build
                    sys.exit(1)
                else:
                    return True # swallow the exception
            else:
                # some kind of unexpected error; propagate it:
                return False
        else:
            # Assume success:
            self.result = True

            # Write the success message:
            if self.okmsg:
                sys.stdout.write('%s\n' % self.okmsg)

    def succeeded(self):
        # Did this test succeed?
        return self.result

class Result:
    pass

class OptionFlag(Result):
    # the outcome of a feature test
    def __init__(self, description, flag, defn):
        self.description = description
        self.flag = flag
        self.defn = defn

    def write_to(self, f):
        f.write('/* %s */\n' % self.description)
        if self.flag:
            f.write('#define %s\n\n' % self.defn)
        else:
            f.write('#undef %s\n\n' % self.defn)

class ConfigBuilder:
    def __init__(self, argv):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('-o', '--output-file')
        args = parser.parse_args(argv[1:])
        #print(args)
        self.filename = args.output_file

        self.dirname = 'config-tests'
        if os.path.exists(self.dirname):
            shutil.rmtree(self.dirname)
        os.mkdir(self.dirname)

        self.testid = 0

        self.results = []

    def make_test_dir(self, test):
        self.testid += 1
        dirname = ('%05i-' % self.testid) + test.initmsg
        dirname = '-'.join(dirname.split())
        dirpath = os.path.join(self.dirname, dirname)
        os.mkdir(dirpath)
        return dirpath

    def write_outcome(self):
        sys.stdout.write('writing %s\n' % self.filename)
        with open(self.filename, 'w') as f:
            f.write('/* autogenerated header file */\n\n')
            for r in self.results:
                r.write_to(f)

    def compile(self, test, src, extraargs):
        dirpath = self.make_test_dir(test)
        srcpath = os.path.join(dirpath, 'feature-test.c')
        with open(srcpath, 'w') as f:
            f.write(src)
        outpath = os.path.join(dirpath, 'feature-test.o')
        args= [os.environ.get('CC', 'gcc'),
               '-c', # don't run the linker (no main)
               '-o', outpath,
               srcpath] + extraargs
        p = Popen(args, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        c = p.wait()
        if c != 0:
            class CompilationError(ConfigurationFailure):
                def __str__(self):
                    result = 'Test compilation failed with exit code %i\n' % c
                    result += '  The command was:\n'
                    result += '    %s\n' % ' '.join(args)
                    result += '  The source was: (in %s)\n' % srcpath
                    result += indent('    ', src) + '\n'
                    result += '  The stderr was:\n'
                    result += indent('    ', stderr) + '\n'
                    return result
            raise CompilationError()

    def capture_shell_output(self, initmsg, cmd):
        with CheckFor(initmsg,
                      mandatory=True) as test:
            out = check_output(cmd,
                               shell=True) # input must be trusted
            out = str(out.decode())
        sys.stdout.write('%s\n' % out.strip())
        return out

    def test_for_mandatory_c_header(self, header, extraargs):
        with CheckFor('checking for %s' % header,
                      okmsg='found',
                      failmsg='not found',
                      mandatory=True) as test:
            self.compile(test,
                         src='#include <%s>' % header,
                         extraargs=extraargs)

    def test_c_compilation(self, initmsg, src, extraargs, description, defn):
        with CheckFor(initmsg,
                      okmsg='yes',
                      failmsg='no',
                      mandatory=False) as test:
            self.compile(test,
                         src,
                         extraargs)
        self.results.append(OptionFlag(description,
                                       test.succeeded(),
                                       defn))

