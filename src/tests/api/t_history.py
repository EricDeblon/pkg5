#!/usr/bin/python2.4
#
# CDDL HEADER START
#
# The contents of this file are subject to the terms of the
# Common Development and Distribution License (the "License").
# You may not use this file except in compliance with the License.
#
# You can obtain a copy of the license at usr/src/OPENSOLARIS.LICENSE
# or http://www.opensolaris.org/os/licensing.
# See the License for the specific language governing permissions
# and limitations under the License.
#
# When distributing Covered Code, include this CDDL HEADER in each
# file and include the License file at usr/src/OPENSOLARIS.LICENSE.
# If applicable, add the following below this CDDL HEADER, with the
# fields enclosed by brackets "[]" replaced with your own identifying
# information: Portions Copyright [yyyy] [name of copyright owner]
#
# CDDL HEADER END
#

# Copyright 2008 Sun Microsystems, Inc.  All rights reserved.
# Use is subject to license terms.

import os
import sys
import tempfile
import shutil
import unittest

import pkg
import pkg.client.history as history
import pkg.misc as misc
import pkg.portable as portable

# Set the path so that modules above can be found
path_to_parent = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, path_to_parent)
import pkg5unittest

class TestHistory(pkg5unittest.Pkg5TestCase):
        # This is to prevent setup() being called for each test.
        persistent_depot = True

        __scratch_dir = None

        __ip_before = """UNEVALUATED:
            +pkg:/SUNWgcc@3.4.3,5.11-0.95:20080807T162946Z"""

        __ip_after = \
            """None -> pkg:/SUNWgcc@3.4.3,5.11-0.95:20080807T162946Z
            None -> pkg:/SUNWbinutils@2.15,5.11-0.95:20080807T153728Z
            None"""

        __errors = [
            "Error 1",
            "Error 2",
        ]

        # Used to store the name of a history file across tests.
        __filename = None

        def setUp(self):
                """Prepare the test for execution.
                """
                self.__scratch_dir = tempfile.mkdtemp()
                # Explicitly convert these to strings as they will be
                # converted by history to deal with minidom issues.
                self.__userid = str(portable.get_userid())
                self.__username = str(portable.get_username())
                self.__h = history.History(root_dir=self.__scratch_dir)
                self.__h.client_name = "pkg-test"

        def tearDown(self):
                """Cleanup after the test execution.
                """
                if self.__scratch_dir:
                        shutil.rmtree(self.__scratch_dir, ignore_errors=True)

        def test_0_valid_operation(self):
                """Verify that operation information can be stored and
                retrieved.
                """
                h = self.__h
                self.assertEqual(os.path.join(self.__scratch_dir, "history"),
                    h.path)

                h.operation_name = "install"
                self.__class__.__filename = os.path.basename(h.pathname)

                # Verify that a valid start time was set.
                misc.timestamp_to_time(h.operation_start_time)

                self.assertEqual("install", h.operation_name)
                self.assertEqual(self.__username, h.operation_username)
                self.assertEqual(self.__userid, h.operation_userid)

                h.operation_start_state = self.__ip_before
                self.assertEqual(self.__ip_before, h.operation_start_state)

                h.operation_end_state = self.__ip_after
                self.assertEqual(self.__ip_after, h.operation_end_state)

                h.operation_errors.extend(self.__errors)
                self.assertEqual(self.__errors, h.operation_errors)

                h.operation_result = history.RESULT_SUCCEEDED

        def test_1_client_info(self):
                """Verify that the client information can be retrieved.
                """
                h = self.__h
                self.assertEqual("pkg-test", h.client_name)
                self.assertEqual(pkg.VERSION, h.client_version)
                # The contents can't really be verified (due to possible
                # platform differences for the first element), but there
                # should be something returned.
                self.assertTrue(h.client_args)

        def test_2_clear(self):
                """Verify that clear actually resets all transient values.
                """
                h = self.__h
                h.clear()
                self.assertEqual(None, h.client_name)
                self.assertEqual(None, h.client_version)
                self.assertFalse(h.client_args)
                self.assertEqual(None, h.operation_name)
                self.assertEqual(None, h.operation_username)
                self.assertEqual(None, h.operation_userid)
                self.assertEqual(None, h.operation_result)
                self.assertEqual(None, h.operation_start_time)
                self.assertEqual(None, h.operation_end_time)
                self.assertEqual(None, h.operation_start_state)
                self.assertEqual(None, h.operation_end_state)
                self.assertEqual(None, h.operation_errors)
                self.assertEqual(None, h.pathname)

        def test_3_client_load(self):
                """Verify that the saved history can be retrieved properly.
                """
                h = history.History(root_dir=self.__scratch_dir,
                    filename=self.__filename)
                # Verify that a valid start time and end time was set.
                misc.timestamp_to_time(h.operation_start_time)
                misc.timestamp_to_time(h.operation_end_time)

                self.assertEqual("install", h.operation_name)
                self.assertEqual(self.__username, h.operation_username)
                self.assertEqual(self.__userid, h.operation_userid)
                self.assertEqual(self.__ip_before, h.operation_start_state)
                self.assertEqual(self.__ip_after, h.operation_end_state)
                self.assertEqual(self.__errors, h.operation_errors)
                self.assertEqual(history.RESULT_SUCCEEDED, h.operation_result)

        def test_4_stacked_operations(self):
                """Verify that multiple operations can be stacked properly (in
                other words, that storage and retrieval works as expected).
                """

                op_stack = {
                    "operation-1": {
                        "start_state": "op-1-start",
                        "end_state": "op-1-end",
                        "result": history.RESULT_SUCCEEDED,
                    },
                    "operation-2": {
                        "start_state": "op-2-start",
                        "end_state": "op-2-end",
                        "result": history.RESULT_FAILED_UNKNOWN,
                    },
                    "operation-3": {
                        "start_state": "op-3-start",
                        "end_state": "op-3-end",
                        "result": history.RESULT_CANCELED,
                    },
                }
                h = self.__h
                h.client_name = "pkg-test"

                for op_name in sorted(op_stack.keys()):
                        h.operation_name = op_name

                for op_name in sorted(op_stack.keys(), reverse=True):
                        op_data = op_stack[op_name]
                        h.operation_start_state = op_data["start_state"]
                        h.operation_end_state = op_data["end_state"]
                        h.operation_result = op_data["result"]

                # Now load all operation data that's been saved during testing
                # for comparison.
                loaded_ops = {}
                for entry in sorted(os.listdir(h.path)):
                        # Load the history entry.
                        he = history.History(root_dir=h.root_dir,
                            filename=entry)

                        loaded_ops[he.operation_name] = {
                                "start_state": he.operation_start_state,
                                "end_state": he.operation_end_state,
                                "result": he.operation_result
                        }

                # Now verify that each operation was saved in the stack and
                # that the correct data was written for each one.
                for op_name in op_stack.keys():
                        op_data = op_stack[op_name]
                        loaded_data = loaded_ops[op_name]
                        self.assertEqual(op_data, loaded_data)

        def test_5_discarded_operations(self):
                """Verify that discarded operations are not saved."""

                h = self.__h
                h.client_name = "pkg-test"

                for op_name in sorted(history.DISCARDED_OPERATIONS):
                        h.operation_name = op_name
                        h.operation_result = history.RESULT_NOTHING_TO_DO

                # Now load all operation data that's been saved during testing
                # for comparison.
                loaded_ops = []
                for entry in sorted(os.listdir(h.path)):
                        # Load the history entry.
                        he = history.History(root_dir=h.root_dir,
                            filename=entry)
                        loaded_ops.append(he.operation_name)

                # Now verify that none of the saved operations are one that
                # should have been discarded.
                for op_name in sorted(history.DISCARDED_OPERATIONS):
                        self.assert_(op_name not in loaded_ops)

if __name__ == "__main__":
        unittest.main()

