#!/usr/bin/env python2
#
#  File: test-afl-sancov.py
#
#  Purpose: Run afl-sancov through a series of tests to ensure proper operations
#           on the local system.
#
#  License (GNU General Public License):
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02111-1301,
#  USA
#

from shutil import rmtree, copy
from aflsancov import *
import unittest
import time
import signal
import os
import json
try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess

class TestAflSanCov(unittest.TestCase):

    ### set a few paths
    tmp_file     = './tmp_cmd.out'
    version_file = '../VERSION'
    afl_cov_cmd  = './aflsancov.py'
    single_generator   = './afl-sancov-generator.sh'
    # parallel_generator = './afl/afl-cov-generator-parallel.sh'
    # afl_cov_live       = './afl/afl-cov-generator-live.sh'

    top_out_dir  = './afl-out'
    sancov_dir = top_out_dir + '/sancov'
    dd_dir = sancov_dir + '/delta-diff'
    expects_dir = './expects'
    expects_ddmode_dir = expects_dir + '/ddmode'
    expects_ddnum_dir = expects_dir + '/ddnum'
    dd_filename1 = '/HARDEN:0001,SESSION000:id:000000,sig:06,src:000003,op:havoc,rep:2.json'
    dd_filename2 = '/HARDEN:0001,SESSION001:id:000000,sig:06,src:000003,op:havoc,rep:4.json'
    dd_file1 = dd_dir + dd_filename1
    dd_file2 = dd_dir + dd_filename2
    expects_ddmode_file1 = expects_ddmode_dir + dd_filename1
    expects_ddmode_file2 = expects_ddmode_dir + dd_filename2
    expects_ddnum_file1 = expects_ddnum_dir + dd_filename1
    expects_ddnum_file2 = expects_ddnum_dir + dd_filename2

    expected_line_substring = 'afl-sancov/tests/test-sancov.c:main:25:3'

#    live_afl_cmd = './fuzzing-wrappers/server-access-redir.sh'
#    live_parallel_afl_cmd = './fuzzing-wrappers/server-access-parallel-redir.sh'

    def do_cmd(self, cmd):
        out = []
        fh = open(self.tmp_file, 'w')
        subprocess.call(cmd, stdin=None,
                stdout=fh, stderr=subprocess.STDOUT, shell=True)
        fh.close()
        with open(self.tmp_file, 'r') as f:
            for line in f:
                out.append(line.rstrip('\n'))
        return out

    def compare_json(self, file1, file2):
        with open(file1) as data_file1:
            data1 = json.load(data_file1)
        with open(file2) as data_file2:
            data2 = json.load(data_file2)
        if data1["shrink-percent"] != data2["shrink-percent"]:
            return False
        if data1["dice-linecount"] != data2["dice-linecount"]:
            return False
        if data1["slice-linecount"] != data2["slice-linecount"]:
            return False
        if data1["diff-node-spec"][0]["count"] != data2["diff-node-spec"][0]["count"]:
            return False
        if self.expected_line_substring not in data1["diff-node-spec"][0]["line"]:
            return False
        if data1["crashing-input"] != data2["crashing-input"]:
            return False
        if 'parent-input' in data1 and 'parent-input' in data2:
            if data1["parent-input"] != data2["parent-input"]:
                return False
        return True

    ### start afl-cov in --live mode - this is for both single and
    ### parallel instance testing
    # def live_init(self):
    #     if is_dir(os.path.dirname(self.top_out_dir)):
    #         if is_dir(self.top_out_dir):
    #             rmtree(self.top_out_dir)
    #     else:
    #         if not is_dir(os.path.dirname(self.top_out_dir)):
    #             os.mkdir(os.path.dirname(self.top_out_dir))
    #
    #     ### start up afl-cov in the background before AFL is running
    #     try:
    #         subprocess.Popen([self.afl_cov_live])
    #     except OSError:
    #         return False
    #     time.sleep(2)
    #     return True

    # def afl_stop(self):
    #
    #     ### stop any afl-fuzz instances
    #     self.do_cmd("%s --stop-afl --afl-fuzzing-dir %s" \
    #             % (self.afl_cov_cmd, self.top_out_dir))
    #
    #     ### now stop afl-cov
    #     afl_cov_pid = get_running_pid(
    #             self.top_out_dir + '/cov/afl-cov-status',
    #             'afl_cov_pid\s+\:\s+(\d+)')
    #     if afl_cov_pid:
    #         os.kill(afl_cov_pid, signal.SIGTERM)
    #
    #     return

    def test_version(self):
        with open(self.version_file, 'r') as f:
            version = f.readline().rstrip()
        self.assertTrue(version
                in ''.join(self.do_cmd("%s --version" % (self.afl_cov_cmd))),
                "afl-sancov --version does not match VERSION file")

    def test_help(self):
        self.assertTrue('--verbose'
                in ''.join(self.do_cmd("%s -h" % (self.afl_cov_cmd))),
                "--verbose not in -h output")

    def test_overwrite_dir(self):
        ### generate coverage, and then try to regenerate without --overwrite
        self.do_cmd("%s --afl-queue-id-limit 1 --overwrite" \
                        % (self.single_generator))

        self.assertTrue(os.path.exists(self.sancov_dir),
                        "No sancov dir generated during invocation")
        out_str = ''.join(self.do_cmd("%s --afl-queue-id-limit 1" \
                        % (self.single_generator)))
        self.assertTrue("use --overwrite" in out_str,
                "Missing --overwrite not caught")

    def test_ddmode(self):
        self.do_cmd("{} --overwrite --dd-mode".format(self.single_generator))
        self.assertTrue(os.path.exists(self.dd_dir),
                        "No delta-diff dir generated during dd-mode invocation")
        self.assertTrue((os.path.exists(self.dd_file1) and os.path.exists(self.dd_file2)),
                        "Missing delta-diff file(s) during dd-mode invocation")

        self.assertTrue(self.compare_json(self.dd_file1, self.expects_ddmode_file1),
                        "Delta-diff file {} does not match".format(self.dd_filename1))
        self.assertTrue(self.compare_json(self.dd_file2, self.expects_ddmode_file2),
                        "Delta-diff file {} does not match".format(self.dd_filename2))

    def test_ddnum(self):
        self.do_cmd("{} --overwrite --dd-mode --dd-num 5".format(self.single_generator))
        self.assertTrue(os.path.exists(self.dd_dir),
                        "No delta-diff dir generated during dd-num invocation")
        self.assertTrue((os.path.exists(self.dd_file1) and os.path.exists(self.dd_file2)),
                        "Missing delta-diff file(s) during dd-num invocation")

        self.assertTrue(self.compare_json(self.dd_file1, self.expects_ddnum_file1),
                        "Delta-diff file {} does not match".format(self.dd_filename1))
        self.assertTrue(self.compare_json(self.dd_file2, self.expects_ddnum_file2),
                        "Delta-diff file {} does not match".format(self.dd_filename2))

    # def test_stop_requires_fuzz_dir(self):
    #     self.assertTrue('Must set'
    #             in ''.join(self.do_cmd("%s --stop-afl" % (self.afl_cov_cmd))),
    #             "--afl-fuzzing-dir missing from --stop-afl mode")

    # def test_func_search_requires_fuzz_dir(self):
    #     self.assertTrue('Must set'
    #             in ''.join(self.do_cmd("%s --func-search test" % (self.afl_cov_cmd))),
    #             "--afl-fuzzing-dir missing from --func-search mode")

    # def test_line_search_requires_fuzz_dir(self):
    #     self.assertTrue('Must set'
    #             in ''.join(self.do_cmd("%s --line-search 1234" % (self.afl_cov_cmd))),
    #             "--afl-fuzzing-dir missing from --line-search mode")

    # def test_live_parallel(self):
    #
    #     if not self.live_init():
    #         return self.assertTrue(False, "Could not run generator cmd: %s" \
    #                 % (self.afl_cov_live))
    #
    #     ### put the wrapper in place
    #     wrapper ='fwknop-afl.git/test/afl/fuzzing-wrappers' + \
    #             '/server-access-parallel-redir.sh'
    #     if os.path.exists(wrapper):
    #         os.remove(wrapper)
    #     copy('afl/server-access-parallel-redir.sh', wrapper)
    #     curr_dir = os.getcwd()
    #     os.chdir('./fwknop-afl.git/test/afl')
    #
    #     ### now start two copies of AFL
    #     try:
    #         subprocess.Popen([self.live_parallel_afl_cmd, "-M", "fuzzer01"])
    #     except OSError:
    #         os.chdir(curr_dir)
    #         return self.assertTrue(False,
    #                 "Could not run live_parallel_afl_cmd: %s -M fuzzer01" \
    #                         % (self.live_parallel_afl_cmd))
    #
    #     try:
    #         subprocess.Popen([self.live_parallel_afl_cmd, "-S", "fuzzer02"])
    #     except OSError:
    #         os.chdir(curr_dir)
    #         return self.assertTrue(False,
    #                 "Could not run live_parallel_afl_cmd: %s -S fuzzer02" \
    #                         % (self.live_parallel_afl_cmd))
    #
    #     os.chdir(curr_dir)
    #
    #     time.sleep(3)
    #
    #     self.afl_stop()
    #
    #     if not (is_dir(self.top_out_dir + '/fuzzer01')
    #             and is_dir(self.top_out_dir + '/fuzzer02')):
    #         return self.assertTrue(False,
    #                 "fuzzer01 or fuzzer02 directory missing")
    #
    #     ### check for the coverage directory since afl-cov should have
    #     ### seen the running AFL instance by now
    #     return self.assertTrue(is_dir(self.top_out_dir + '/cov'),
    #             "live coverage directory '%s' does not exist" \
    #                     % (self.top_out_dir + '/cov'))
    #
    # def test_live(self):
    #
    #     if not self.live_init():
    #         return self.assertTrue(False, "Could not run generator cmd: %s" \
    #                 % (self.afl_cov_live))
    #
    #     ### put the wrapper in place
    #     wrapper = 'fwknop-afl.git/test/afl/fuzzing-wrappers/server-access-redir.sh'
    #     if os.path.exists(wrapper):
    #         os.remove(wrapper)
    #     copy('afl/server-access-redir.sh', wrapper)
    #     curr_dir = os.getcwd()
    #     os.chdir('./fwknop-afl.git/test/afl')
    #
    #     ### now start AFL and let it run for longer than --sleep in the
    #     ### generator script - then look for the coverage directory
    #     try:
    #         subprocess.Popen([self.live_afl_cmd])
    #     except OSError:
    #         os.chdir(curr_dir)
    #         return self.assertTrue(False,
    #                 "Could not run live_afl_cmd: %s" % (self.live_afl_cmd))
    #     os.chdir(curr_dir)
    #
    #     time.sleep(3)
    #
    #     self.afl_stop()
    #
    #     ### check for the coverage directory since afl-cov should have
    #     ### seen the running AFL instance by now
    #     return self.assertTrue(is_dir(self.top_out_dir + '/cov'),
    #             "live coverage directory '%s' does not exist" \
    #                     % (self.top_out_dir + '/cov'))

    # def test_queue_limit_5(self):
    #     out_str = ''.join(self.do_cmd("%s --afl-queue-id-limit 5 --overwrite" \
    #                     % (self.single_generator)))
    #     self.assertTrue('Final lcov web report' in out_str
    #             and "New 'line' coverage: 1571" in out_str)
    #
    # def test_queue_limit_5_parallel(self):
    #     out_str = ''.join(self.do_cmd("%s --afl-queue-id-limit 5 --overwrite" \
    #                     % (self.parallel_generator)))
    #     self.assertTrue('Final lcov web report' in out_str
    #             and "New 'line' coverage: 1571" in out_str
    #             and "Imported 145 new test cases" in out_str
    #             and "Imported 212 new test cases" in out_str)

if __name__ == "__main__":
    unittest.main()
