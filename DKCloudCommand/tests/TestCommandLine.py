import re

__author__ = 'DataKitchen, Inc.'
import unittest
import os
import shutil
import tempfile
import datetime
import time
import random
from os.path import expanduser
from sys import path
from click.testing import CliRunner
from BaseTestCloud import *
from DKFileHelper import DKFileHelper
from DKCloudCommand.cli.__main__ import dk
from DKKitchenDisk import DKKitchenDisk
from shutil import copy
from DKPathHelper import DKPathHelper

from DKModules.DKJSONParser import DKJSONParser

class TestCommandLine(BaseTestCloud):
    if DKPathHelper.is_windows_os():
        _TEMPFILE_LOCATION = 'c:\\temp'
    else:
        _TEMPFILE_LOCATION = '/var/tmp'
    SLEEP_TIME = 5

    # ------------------------------------------------------------------------------------------------------------------
    #  Basic Commands
    # ------------------------------------------------------------------------------------------------------------------

    def test_alias(self):
        runner = CliRunner()
        result = runner.invoke(dk, ["--help"])
        rv = result.output
        self.assertTrue('kitchen-create (kc)' in rv)
        self.assertTrue('orderrun-delete (ord)' in rv)

        result = runner.invoke(dk, ["kl"])
        rv = result.output
        self.assertTrue('CLI-Top' in rv)

    def test_user_info(self):
        runner = CliRunner()
        result = runner.invoke(dk, ["user-info"])

        self.assertEqual(0, result.exit_code, result.output)
        splitted_output = result.output.split('\n')

        index = 0
        stage = 1
        while index < len(splitted_output):
            if stage == 1:
                if 'Name:' in splitted_output[index] and EMAIL_SUFFIX in splitted_output[index]:
                    stage += 1
                index += 1
                continue
            if stage == 2:
                if 'Email:' in splitted_output[index] and EMAIL_SUFFIX in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 3:
                if 'Customer Name:' in splitted_output[index] and 'DataKitchen' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 4:
                if 'Support Email:' in splitted_output[index] and '@datakitchen.io' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 5:
                if 'Role:' in splitted_output[index] and ('ADMIN' in splitted_output[index] or 'IT' in splitted_output[index]):
                    stage += 1
                index += 1
                continue
            index += 1

        self.assertEqual(6,stage)

    def test_contexts(self):
        # Test Cleanup
        self._delete_context('test03', skip_checks=True)
        self._delete_context('test02', skip_checks=True)
        self._delete_context('test01', skip_checks=True)

        # Initial check
        expected_context_list = ['default', 'test']
        unexpected_context_list = ['test01', 'test02', 'test03']
        current_context = 'test'
        self.assertTrue(self._check_contexts(expected_context_list, unexpected_context_list, current_context))

        # Create test contexts
        self.assertTrue(self._create_context('test01'))
        self.assertTrue(self._create_context('test02'))
        self.assertTrue(self._create_context('test03'))

        expected_context_list = ['default', 'test', 'test01', 'test02', 'test03']
        unexpected_context_list = []
        current_context = 'test'
        self.assertTrue(self._check_contexts(expected_context_list, unexpected_context_list, current_context))

        # Context switch
        self.assertTrue(self._context_switch('test02'))

        expected_context_list = ['default', 'test', 'test01', 'test02', 'test03']
        unexpected_context_list = []
        current_context = 'test02'
        self.assertTrue(self._check_contexts(expected_context_list, unexpected_context_list, current_context))

        # Context switch
        self.assertTrue(self._context_switch('test'))

        expected_context_list = ['default', 'test', 'test01', 'test02', 'test03']
        unexpected_context_list = []
        current_context = 'test'
        self.assertTrue(self._check_contexts(expected_context_list, unexpected_context_list, current_context))

        # Working path check
        cfg = DKCloudCommandConfig()
        home = expanduser('~')  # does not end in a '/'
        dk_temp_folder = os.path.join(home, '.dk')
        cfg.set_dk_temp_folder(dk_temp_folder)
        general_config_file_data = DKFileHelper.read_file(cfg.get_general_config_file_location())
        general_config_dict = json.loads(general_config_file_data)
        self.assertTrue(general_config_dict[cfg.DK_CHECK_WORKING_PATH], 'Configure %s as true at {HOME}/.dk/general-config.json' % cfg.DK_CHECK_WORKING_PATH)

        orig_dir = os.getcwd()
        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        working_dir = os.path.join(temp_dir, 'test02', 'myfolder')
        os.makedirs(working_dir)
        os.chdir(working_dir)

        runner = CliRunner()
        result = runner.invoke(dk, ["kl"])
        rv = result.output
        os.chdir(orig_dir)
        message = 'Warning: context name "test02" shows up in your current working path,\nbut your current context is "test".'
        self.assertTrue(message in rv)

        # Delete test contexts
        self.assertTrue(self._delete_context('test03'))
        self.assertTrue(self._delete_context('test02'))
        self.assertTrue(self._delete_context('test01'))

        # Final check
        expected_context_list = ['default', 'test']
        unexpected_context_list = ['test01', 'test02', 'test03']
        current_context = 'test'
        self.assertTrue(self._check_contexts(expected_context_list, unexpected_context_list, current_context))

        # Remove temp files
        shutil.rmtree(temp_dir, ignore_errors=True)

    def _context_switch(self, context_name):
        runner = CliRunner()
        result = runner.invoke(dk, ["context-switch", "--yes", context_name])
        self.assertEqual(0, result.exit_code, result.output)
        delete_message = 'Switching to context %s' % context_name
        self.assertTrue(delete_message in result.output)
        self.assertTrue('Context switch done.' in result.output)

        # Check file system
        home = expanduser('~')
        context_file_path = os.path.join(home, '.dk', '.context')
        context_file_contents = DKFileHelper.read_file(context_file_path)
        self.assertEqual(context_name, context_file_contents)

        context_folder_path = os.path.join(home, '.dk', context_name)
        self.assertTrue(os.path.exists(context_folder_path))
        return True

    def _delete_context(self, context_name, skip_checks=False):
        runner = CliRunner()
        result = runner.invoke(dk, ["context-delete", "--yes", context_name])
        if not skip_checks:
            self.assertEqual(0, result.exit_code, result.output)
            delete_message = 'Deleting context %s' % context_name
            self.assertTrue(delete_message in result.output)
            self.assertTrue('Done!' in result.output)

        # Check file system
        home = expanduser('~')
        full_path = os.path.join(home, '.dk', context_name)
        if os.path.exists(full_path):
            return False

        return True

    def _create_context(self, context_name):
        home = expanduser('~')
        source = os.path.join(home, '.dk', 'test')
        target = os.path.join(home, '.dk', context_name)
        shutil.copytree(source, target)
        return True

    def _check_contexts(self, expected_context_list, unexpected_context_list=[], current_context='test'):
        runner = CliRunner()
        result = runner.invoke(dk, ["context-list"])
        self.assertEqual(0, result.exit_code, result.output)
        splitted_output = result.output.split('\n')

        found_title = False

        index = 0
        stage = 1
        while index < len(splitted_output):
            if stage == 1:
                if 'Available contexts are ...' in splitted_output[index]: found_title = True
                index += 1
                continue
        if not found_title:
            return False

        current_context_legend = 'Current context is: %s' % current_context
        if current_context_legend not in result.output:
            return False

        for context in unexpected_context_list:
            if context in result.output:
                return False

        for context in expected_context_list:
            if context not in result.output:
                return False
        return True

    def test_config_list(self):
        runner = CliRunner()
        result = runner.invoke(dk, ["config-list"])

        self.assertEqual(0, result.exit_code, result.output)
        splitted_output = result.output.split('\n')

        index = 0
        stage = 1
        while index < len(splitted_output):
            if stage == 1:
                if 'Current configuration is ...' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 2:
                if 'Config Location:' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 3:
                if 'General Config Location:' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 4:
                if 'Username:' in splitted_output[index] and EMAIL_SUFFIX in splitted_output[index]: stage += 1  # skip-secret-check
                index += 1
                continue
            if stage == 5:
                if 'Password:' in splitted_output[index]: stage += 1  # skip-secret-check
                index += 1
                continue
            if stage == 6:
                if 'Cloud IP:' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 7:
                if 'Cloud Port:' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 8:
                if 'Merge Tool:' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 9:
                if 'Diff Tool:' in splitted_output[index]: stage += 1
                index += 1
                continue
            index += 1

        self.assertEqual(10, stage)

    # ------------------------------------------------------------------------------------------------------------------
    #  Kitchen Basic Commands
    # ------------------------------------------------------------------------------------------------------------------

    def test_kitchen_config(self):
        runner = CliRunner()
        result = runner.invoke(dk, ["kitchen-config", "--list"])
        rv = result.output

    def test_a_kitchen_list(self):
        tv1 = 'CLI-Top'
        tv2 = 'kitchens-plus'
        tv3 = 'master'
        runner = CliRunner()
        result = runner.invoke(dk, ['kitchen-list'])
        rv = result.output
        self.assertTrue(tv1 in rv)
        self.assertTrue(tv2 in rv)
        self.assertTrue(tv3 in rv)

    def test_kitchen_which(self):

        kn = 'bobo'
        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        os.chdir(temp_dir)
        DKKitchenDisk.write_kitchen(kn, temp_dir)
        os.chdir(os.path.join(temp_dir, kn))

        runner = CliRunner()
        result = runner.invoke(dk, ['kitchen-which'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn('bobo', result.output)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_kitchen_get(self):
        tk = 'CLI-Top'
        recipe1 = 'simple'
        recipe2 = 'parallel-recipe-test'
        runner = CliRunner()

        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        os.chdir(temp_dir)
        result = runner.invoke(dk, ['kitchen-get', tk, '--recipe', recipe1, '--recipe', recipe2])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual(os.path.isdir(os.path.join(temp_dir, tk, recipe1)), True)
        self.assertTrue(DKPathHelper.normalize('simple/node2/data_sinks', DKPathHelper.WIN) in result.output)
        self.assertTrue(DKPathHelper.normalize('parallel-recipe-test/node1/data_sources', DKPathHelper.WIN) in result.output)
        shutil.rmtree(temp_dir, ignore_errors=True)

        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        os.chdir(temp_dir)
        result = runner.invoke(dk, ['kitchen-get', tk])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual(os.path.isdir(os.path.join(temp_dir, tk, '.dk')), True)
        self.assertEqual(os.path.isfile(os.path.join(temp_dir, tk, '.dk', 'KITCHEN_META')), True)
        shutil.rmtree(temp_dir, ignore_errors=True)

        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        os.chdir(temp_dir)
        result = runner.invoke(dk, ['kitchen-get', tk, '--recipe', recipe1])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual(os.path.isdir(os.path.join(temp_dir, tk, recipe1)), True)
        self.assertTrue(DKPathHelper.normalize('simple/node2/data_sinks', DKPathHelper.WIN) in result.output)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_kitchen_create(self):
        parent = 'CLI-Top'
        kitchen = 'temp-create-kitchen-CL'
        kitchen = self._add_my_guid(kitchen)
        runner = CliRunner()

        result = runner.invoke(dk, ['kitchen-delete', kitchen, '--yes'])
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent, kitchen])
        self.assertEqual(0, result.exit_code, result.output)
        result2 = runner.invoke(dk, ['kitchen-list'])
        self.assertEqual(0, result2.exit_code, result.output)
        rv = result2.output
        self.assertTrue(kitchen in rv)  # kitchen should be in the list

        result = runner.invoke(dk, ['kitchen-delete', kitchen, '--yes'])
        self.assertEqual(0, result.exit_code, result.output)

    def test_kitchen_delete(self):
        parent = 'CLI-Top'
        kitchen = 'temp-delete-kitchen-CL'
        kitchen = self._add_my_guid(kitchen)
        runner = CliRunner()

        runner.invoke(dk, ['kitchen-delete', kitchen, '--yes'])
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent, kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        result = runner.invoke(dk, ['kitchen-delete', kitchen, '--yes'])
        self.assertEqual(0, result.exit_code, result.output)
        result2 = runner.invoke(dk, ['kitchen-list'])
        self.assertEqual(0, result2.exit_code, result2.output)
        self.assertTrue(kitchen not in result2.output)  # kitchen should not be in the list

    # ------------------------------------------------------------------------------------------------------------------
    #  Kitchen Merge Commands
    # ------------------------------------------------------------------------------------------------------------------

    def test_merge_kitchens_no_changes(self):
        clean_up = True

        existing_kitchen_name = 'master'
        base_test_kitchen_name = 'base-test-kitchen'
        base_test_kitchen_name = self._add_my_guid(base_test_kitchen_name)
        branched_test_kitchen_name = 'branched-from-base-test-kitchen'
        branched_test_kitchen_name = self._add_my_guid(branched_test_kitchen_name)

        # setup
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', branched_test_kitchen_name, '--yes'])
        runner.invoke(dk, ['kitchen-delete', base_test_kitchen_name, '--yes'])
        # test
        # create base kitchen
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '-p', existing_kitchen_name,
                                    base_test_kitchen_name])
        self.assertEqual(0, result.exit_code, result.output)
        # create branch kitchen from base kitchen
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '-p', base_test_kitchen_name,
                                    branched_test_kitchen_name])
        self.assertEqual(0, result.exit_code, result.output)

        # do merge preview
        result = runner.invoke(dk, ['kitchen-merge-preview', '--source_kitchen', branched_test_kitchen_name,
                                    '--target_kitchen', base_test_kitchen_name,
                                    '-cpr'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Previewing merge Kitchen' in result.output)
        self.assertTrue('Merge Preview Results' in result.output)
        self.assertTrue('Nothing to merge.' in result.output)
        self.assertTrue('Kitchen merge preview done.' in result.output)

        url_string = 'Url: \thttps://ghe.datakitchen.io/api/v3/DataKitchen/DKCustomers/compare/%s...%s' % (base_test_kitchen_name, branched_test_kitchen_name)
        self.assertTrue(url_string in result.output)
        self.assertTrue('Url:' in result.output)

        # do merge
        result = runner.invoke(dk, ['kitchen-merge', '--source_kitchen', branched_test_kitchen_name,
                                    '--target_kitchen', base_test_kitchen_name,
                                    '--yes'])
        self.assertEqual(0, result.exit_code, result.output)
        self._check_no_merge_conflicts(result.output)

        # cleanup
        if clean_up:
            runner.invoke(dk, ['kitchen-delete', branched_test_kitchen_name, '--yes'])
            runner.invoke(dk, ['kitchen-delete', base_test_kitchen_name, '--yes'])

    def test_merge_kitchens_changes(self):
        self.assertTrue(True)
        base_kitchen = 'CLI-Top'
        parent_kitchen = self._add_my_guid('merge_changes_parent')
        child_kitchen = self._add_my_guid('merge_changes_child')
        recipe = 'simple'
        new_file = 'new-file.txt'
        new_file2 = 'new-file2.txt'
        new_dir = 'new-dir'

        temp_dir_child, kitchen_dir_child, recipe_dir_child = self._make_recipe_dir(recipe, child_kitchen)
        temp_dir_parent, kitchen_dir_parent, recipe_dir_parent = self._make_recipe_dir(recipe, parent_kitchen)

        runner = CliRunner()

        setup = True
        cleanup = True
        if setup:
            result = runner.invoke(dk, ['kitchen-delete', child_kitchen, '--yes'])
            result = runner.invoke(dk, ['kitchen-delete', parent_kitchen, '--yes'])

            time.sleep(TestCommandLine.SLEEP_TIME)
            result = runner.invoke(dk, ['kitchen-create', '--parent', base_kitchen, parent_kitchen])
            self.assertTrue(0 == result.exit_code)

            time.sleep(TestCommandLine.SLEEP_TIME)
            result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, child_kitchen])
            self.assertTrue(0 == result.exit_code)

            # get parent recipe
            os.chdir(kitchen_dir_child)
            result = runner.invoke(dk, ['recipe-get', recipe])
            rv = result.output
            self.assertTrue(recipe in rv)
            self.assertTrue(os.path.exists(recipe))

            # change the file and add to child kitchen
            os.chdir(recipe_dir_child)
            with open(new_file, 'w') as f:
                f.write('line1\nchild\nline2\n')
            message = 'adding %s to %s' % (new_file, child_kitchen)
            result = runner.invoke(dk, ['file-update',
                                        '--kitchen', child_kitchen,
                                        '--recipe', recipe,
                                        '--message', message,
                                        new_file])
            self.assertEqual(0, result.exit_code, result.output)

            os.mkdir(new_dir)
            new_file2_path = os.path.join(new_dir, new_file2)
            with open(new_file2_path, 'w') as f:
                f.write('my new file 2\n')

            message = 'adding %s to %s' % (new_file2, child_kitchen)
            result = runner.invoke(dk, ['file-update',
                                        '--kitchen', child_kitchen,
                                        '--recipe', recipe,
                                        '--message', message,
                                        new_file2_path])
            self.assertEqual(0, result.exit_code, result.output)

        # do merge preview
        os.chdir(temp_dir_child)
        result = runner.invoke(dk, ['kitchen-merge-preview',
                                    '--source_kitchen', child_kitchen,
                                    '--target_kitchen', parent_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        splitted_output = result.output.split('\n')

        index = 0
        stage = 1
        while index < len(splitted_output):
            if stage == 1:
                if 'Previewing merge Kitchen' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 2:
                if 'Merge Preview Results' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 3:
                if 'ok' in splitted_output[index] and os.path.normpath('simple/new-file.txt') in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 4:
                if 'Kitchen merge preview done.' in splitted_output[index]: stage += 1
                index += 1
                continue
            index += 1

        self.assertEqual(5, stage)

        # do merge
        result = runner.invoke(dk, ['kitchen-merge',
                                    '--source_kitchen', child_kitchen,
                                    '--target_kitchen', parent_kitchen,
                                    '--yes'])
        self.assertEqual(0, result.exit_code, result.output)

        splitted_output = result.output.split('\n')

        index = 0
        stage = 1
        while index < len(splitted_output):
            if stage == 1:
                if 'looking for manually merged files' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 2:
                if 'Calling Merge ...' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 3:
                if os.path.normpath('simple/new-dir/new-file2.txt') in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 4:
                url = '/dk/index.html#/history/dk/'
                if 'Url:' in splitted_output[index] and url in splitted_output[index]: stage += 1
                index += 1
                continue
            index += 1

        self.assertEqual(5, stage)

        if cleanup:
            runner.invoke(dk, ['kitchen-delete', child_kitchen, '--yes'])
            runner.invoke(dk, ['kitchen-delete', parent_kitchen, '--yes'])
            shutil.rmtree(temp_dir_child, ignore_errors=True)
            shutil.rmtree(temp_dir_parent, ignore_errors=True)

    def test_merge_kitchens_changes_manual(self):
        self.assertTrue(True)
        base_kitchen = 'CLI-Top'
        parent_kitchen = 'merge_resolve_parent'
        parent_kitchen = self._add_my_guid(parent_kitchen)
        child_kitchen = 'merge_resolve_child'
        child_kitchen = self._add_my_guid(child_kitchen)
        recipe = 'simple'
        conflicted_file = 'conflicted-file.txt'

        self.assertTrue(True)

        temp_dir_child, kitchen_dir_child, recipe_dir_child = self._make_recipe_dir(recipe, child_kitchen)
        temp_dir_parent, kitchen_dir_parent, recipe_dir_parent = self._make_recipe_dir(recipe, parent_kitchen)

        runner = CliRunner()

        setup = True
        cleanup = True
        if setup:
            result = runner.invoke(dk, ['kitchen-delete', child_kitchen, '--yes'])
            result = runner.invoke(dk, ['kitchen-delete', parent_kitchen, '--yes'])

            time.sleep(TestCommandLine.SLEEP_TIME)
            result = runner.invoke(dk, ['kitchen-create', '--parent', base_kitchen, parent_kitchen])
            self.assertEqual(0, result.exit_code, result.output)

            time.sleep(TestCommandLine.SLEEP_TIME)
            result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, child_kitchen])
            self.assertEqual(0, result.exit_code, result.output)

            # get parent recipe
            os.chdir(kitchen_dir_parent)
            result = runner.invoke(dk, ['recipe-get', recipe])
            rv = result.output
            self.assertTrue(recipe in rv)
            self.assertTrue(os.path.exists(recipe))

            # change the conflicted file and add to parent kitchen
            os.chdir(recipe_dir_parent)
            with open(conflicted_file, 'w') as f:
                f.write('line1\nparent\nline2\n')
            message = 'adding %s to %s' % (conflicted_file, parent_kitchen)
            result = runner.invoke(dk, ['file-update',
                                        '--kitchen', parent_kitchen,
                                        '--recipe', recipe,
                                        '--message', message,
                                        conflicted_file])
            self.assertEqual(0, result.exit_code, result.output)

            # change the conflicted file and add to child kitchen
            os.chdir(recipe_dir_child)
            with open(conflicted_file, 'w') as f:
                f.write('line1\nchild\nline2\n')
            message = 'adding %s to %s' % (conflicted_file, child_kitchen)
            result = runner.invoke(dk, ['file-update',
                                        '--kitchen', child_kitchen,
                                        '--recipe', recipe,
                                        '--message', message,
                                        conflicted_file])
            self.assertEqual(0, result.exit_code, result.output)

        # do merge preview
        os.chdir(temp_dir_parent)
        result = runner.invoke(dk, ['kitchen-merge-preview',
                                    '--source_kitchen', child_kitchen,
                                    '--target_kitchen', parent_kitchen,
                                    '-cpr'])
        self.assertEqual(0, result.exit_code, result.output)

        splitted_output = result.output.split('\n')

        index = 0
        stage = 1
        while index < len(splitted_output):
            if stage == 1:
                if 'Previewing merge Kitchen' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 2:
                if 'Merge Preview Results' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 3:
                if 'conflict' in splitted_output[index] and os.path.normpath('simple/conflicted-file.txt') in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 4:
                if 'Kitchen merge preview done.' in splitted_output[index]: stage += 1
                index += 1
                continue
            index += 1

        self.assertEqual(5, stage)

        # do merge without resolving conflicts
        result = runner.invoke(dk, ['kitchen-merge',
                                    '--source_kitchen', child_kitchen,
                                    '--target_kitchen', parent_kitchen,
                                    '--yes'])
        self.assertNotEqual(0, result.exit_code, result.output)

        splitted_output = result.output.split('\n')

        index = 0
        stage = 1
        while index < len(splitted_output):
            if stage == 1:
                if 'Merging Kitchen' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 2:
                if 'looking for manually merged files in temporary directory' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 3:
                if 'There are unresolved conflicts, please resolve through the following sequence of commands' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 4:
                if 'Offending file encountered is: conflicted-file.txt.base' in splitted_output[index]: stage += 1
                index += 1
                continue
            index += 1

        self.assertEqual(5, stage)

        # Resolve the conflict
        base_working_dir = self._api.get_merge_dir()
        path1 = '%s' % base_working_dir
        path2 = '%s_to_%s' % (child_kitchen, parent_kitchen)
        working_dir = os.path.join(path1, path2)
        file_name = 'conflicted-file.txt'
        full_path = os.path.join(working_dir, recipe, file_name)

        with open('%s.base' % full_path, 'w') as f:
            f.write('line1\nmerged\nline2\n')

        result = runner.invoke(dk, ['file-resolve',
                                    '--source_kitchen', child_kitchen,
                                    '--target_kitchen', parent_kitchen,
                                    os.path.normpath('simple/%s' % file_name)])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('File resolve for file %s' % os.path.normpath('simple/conflicted-file.txt') in result.output)
        self.assertTrue('File resolve done.' in result.output)

        resolved_contents = DKFileHelper.read_file('%s.resolved' % full_path)
        self.assertTrue('line1' in resolved_contents)
        self.assertTrue('merged' in resolved_contents)
        self.assertTrue('line2' in resolved_contents)

        # do merge preview after resolving conflicts
        result = runner.invoke(dk, ['kitchen-merge-preview',
                                    '--source_kitchen', child_kitchen,
                                    '--target_kitchen', parent_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        splitted_output = result.output.split('\n')

        index = 0
        stage = 1
        while index < len(splitted_output):
            if stage == 1:
                if 'Previewing merge Kitchen' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 2:
                if 'Merge Preview Results' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 3:
                if 'resolved' in splitted_output[index] and os.path.normpath('simple/conflicted-file.txt') in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 4:
                if 'Kitchen merge preview done.' in splitted_output[index]: stage += 1
                index += 1
                continue
            index += 1

        self.assertEqual(5,stage)

        # do merge
        result = runner.invoke(dk, ['kitchen-merge',
                                    '--source_kitchen', child_kitchen,
                                    '--target_kitchen', parent_kitchen,
                                    '--yes'])
        self.assertEqual(0,result.exit_code)

        splitted_output = result.output.split('\n')

        index = 0
        stage = 1
        while index < len(splitted_output):
            if stage == 1:
                if 'looking for manually merged files' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 2:
                if 'Found' in splitted_output[index] and os.path.normpath('/simple/conflicted-file.txt.resolved') in splitted_output[index] : stage += 1
                index += 1
                continue
            if stage == 3:
                if 'Calling Merge with manual resolved conflicts ...' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 4:
                if 'Merge done.' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 5:
                url = '/dk/index.html#/history/dk/'
                if 'Url:' in splitted_output[index] and url in splitted_output[index]: stage += 1
                index += 1
                continue

            index += 1

        self.assertEqual(6,stage)

        if cleanup:
            runner.invoke(dk, ['kitchen-delete', child_kitchen, '--yes'])
            runner.invoke(dk, ['kitchen-delete', parent_kitchen, '--yes'])
            shutil.rmtree(temp_dir_child, ignore_errors=True)
            shutil.rmtree(temp_dir_parent, ignore_errors=True)

    # ------------------------------------------------------------------------------------------------------------------
    #  Recipe Commands
    # ------------------------------------------------------------------------------------------------------------------

    def test_recipe_list(self):
        tv1 = 's3-small-recipe'
        tv2 = 'simple'
        tv3 = 'parallel-recipe-test'
        kitchen_name = 'CLI-Top'
        runner = CliRunner()
        result = runner.invoke(dk, ['recipe-list', '--kitchen', kitchen_name])
        rv = result.output
        self.assertTrue(tv1 in rv)
        self.assertTrue(tv2 in rv)
        self.assertTrue(tv3 in rv)

        temp_dir, kitchen_dir = self._make_kitchen_dir(kitchen_name, change_dir=True)
        result = runner.invoke(dk, ['recipe-list'])
        rv = result.output
        self.assertTrue(tv1 in rv)
        self.assertTrue(tv2 in rv)
        self.assertTrue(tv3 in rv)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recipe_get(self):
        tv = 'simple'
        kn = 'CLI-Top'

        temp_dir, kitchen_dir = self._make_kitchen_dir(kn, change_dir=True)

        runner = CliRunner()
        result = runner.invoke(dk, ['recipe-get', tv])
        rv = result.output
        self.assertTrue(tv in rv)
        self.assertTrue(os.path.exists(tv))
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recipe_get_status(self):
        tv = 'simple'
        kn = 'CLI-Top'
        runner = CliRunner()

        # Get something to compare against.
        temp_dir, kitchen_dir = self._make_kitchen_dir(kn, change_dir=True)
        runner.invoke(dk, ['recipe-get', tv])

        new_path = os.path.join(kitchen_dir, tv)
        os.chdir(new_path)
        result = runner.invoke(dk, ['recipe-status'])
        self.assertEqual(result.exit_code, 0)
        self.assertFalse('error' in result.output)

        match = re.search(r"([0-9]*) files are unchanged", result.output)
        self.assertTrue(int(match.group(1)) >= 15)
        self.assertTrue('files are unchanged' in result.output)

        os.chdir(os.path.split(new_path)[0])
        result = runner.invoke(dk, ['recipe-status'])
        self.assertTrue('error' in result.output.lower())
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_update_all_files(self):
        # setup
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'CLI-test_update_file'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        recipe_file_key = recipe_name
        file_name = 'description.json'
        message = 'test update CLI-test_update_file'
        api_file_key = file_name
        update_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        runner = CliRunner()  # for the CLI level
        runner.invoke(dk, ['kitchen-delete', test_kitchen, '--yes'])
        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)

        DKKitchenDisk.write_kitchen(parent_kitchen, temp_dir)
        parent_kitchen_dir = os.path.join(temp_dir, parent_kitchen)
        os.chdir(parent_kitchen_dir)
        original_file = self._get_recipe_file_contents(runner, parent_kitchen, recipe_name, recipe_file_key, file_name)
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, test_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        DKKitchenDisk.write_kitchen(test_kitchen, temp_dir)
        test_kitchen_dir = os.path.join(temp_dir, test_kitchen)
        os.chdir(test_kitchen_dir)
        new_kitchen_file = self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                          recipe_file_key, file_name, temp_dir)
        self.assertEqual(original_file, new_kitchen_file)
        new_kitchen_file_dict = self._get_the_dict(new_kitchen_file)
        new_kitchen_file_abspath = os.path.join(test_kitchen_dir, os.path.join(recipe_file_key, file_name))
        new_kitchen_file_dict[test_kitchen] = update_str
        new_kitchen_file2 = self._get_the_json_str(new_kitchen_file_dict)
        with open(new_kitchen_file_abspath, 'w') as rfile:
            rfile.seek(0)
            rfile.truncate()
            rfile.write(new_kitchen_file2)
        # test
        orig_dir = os.getcwd()
        working_dir = os.path.join(test_kitchen_dir, recipe_name)
        os.chdir(working_dir)
        result = runner.invoke(dk, ['recipe-update', '--message', message])
        os.chdir(orig_dir)
        self.assertTrue('ERROR' not in result.output)
        new_kitchen_file3 = self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                           recipe_file_key, file_name)
        new_kitchen_file2_formatted = DKJSONParser.format_file(new_kitchen_file2)
        self.assertEqual(new_kitchen_file2_formatted, new_kitchen_file3)

        # cleanup
        runner.invoke(dk, ['kitchen-delete', '--kitchen', test_kitchen, '--yes'])
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_update_file(self):
        # setup
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'CLI-test_update_file'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        recipe_file_key = recipe_name
        file_name = 'description.json'
        message = 'test update CLI-test_update_file'
        api_file_key = file_name
        update_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        runner = CliRunner()  # for the CLI level
        runner.invoke(dk, ['kitchen-delete', test_kitchen, '--yes'])
        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)

        DKKitchenDisk.write_kitchen(parent_kitchen, temp_dir)
        parent_kitchen_dir = os.path.join(temp_dir, parent_kitchen)
        os.chdir(parent_kitchen_dir)
        original_file = self._get_recipe_file_contents(runner, parent_kitchen, recipe_name, recipe_file_key, file_name)
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, test_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        DKKitchenDisk.write_kitchen(test_kitchen, temp_dir)
        test_kitchen_dir = os.path.join(temp_dir, test_kitchen)
        os.chdir(test_kitchen_dir)
        new_kitchen_file = self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                          recipe_file_key, file_name, temp_dir)
        self.assertEqual(original_file, new_kitchen_file)
        new_kitchen_file_dict = self._get_the_dict(new_kitchen_file)
        new_kitchen_file_abspath = os.path.join(test_kitchen_dir, os.path.join(recipe_file_key, file_name))
        new_kitchen_file_dict[test_kitchen] = update_str
        new_kitchen_file2 = self._get_the_json_str(new_kitchen_file_dict)
        with open(new_kitchen_file_abspath, 'w') as rfile:
            rfile.seek(0)
            rfile.truncate()
            rfile.write(new_kitchen_file2)
        # test
        orig_dir = os.getcwd()
        working_dir = os.path.join(test_kitchen_dir, recipe_name)
        os.chdir(working_dir)
        result = runner.invoke(dk, ['file-update',
                                    '--recipe', recipe_name,
                                    '--message', message,
                                    api_file_key])
        os.chdir(orig_dir)
        self.assertTrue('ERROR' not in result.output)
        new_kitchen_file3 = self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                           recipe_file_key, file_name)
        new_kitchen_file2_formatted = DKJSONParser.format_file(new_kitchen_file2)
        self.assertEqual(new_kitchen_file2_formatted, new_kitchen_file3)

        # cleanup
        runner.invoke(dk, ['kitchen-delete', '--kitchen', test_kitchen, '--yes'])
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_file(self):
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'test_create_file-Runner'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        file_name = 'added.sql'
        filedir = 'resources'
        recipe_file_key = os.path.join(recipe_name, filedir)
        api_file_key = os.path.join(filedir, file_name)
        file_contents = '--\n-- sql for you\n--\n\nselect 1024\n\n'
        message = 'test update test_create_file-API'
        runner = CliRunner()

        # create test kitchen
        runner.invoke(dk, ['kitchen-delete', test_kitchen, '--yes'])
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, test_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        # make and cd to kitchen dir and get the recipe to disk
        temp_dir = tempfile.mkdtemp(prefix='unit-test_create_file', dir=TestCommandLine._TEMPFILE_LOCATION)

        DKKitchenDisk.write_kitchen(test_kitchen, temp_dir)
        kd = os.path.join(temp_dir, test_kitchen)
        orig_dir = os.getcwd()
        os.chdir(kd)
        self._get_recipe(runner, recipe_name)

        # create new file on disk
        try:
            os.chdir(recipe_name)
            f = open(api_file_key, 'w')
            f.write(file_contents)
            f.close()
        except ValueError, e:
            print('could not write file %s.' % e)
            self.assertTrue(False)

        # add file from disk THE TEST
        result = runner.invoke(dk, ['file-update',
                                    '--kitchen', test_kitchen,
                                    '--recipe', recipe_name,
                                    '--message', message,
                                    api_file_key
                                    ])
        self.assertTrue('ERROR' not in result.output.lower())

        # make sure file is in kitchen (get file)
        file_contents2 = self._get_recipe_file_contents(runner, test_kitchen, recipe_name, recipe_file_key, file_name)
        self.assertEqual(file_contents, file_contents2, 'Create check')

        # Now a negative file-update case
        graph_file = 'graph.json'
        graph_file_path = os.path.join(kd, recipe_name, graph_file)
        file_contents = DKFileHelper.read_file(graph_file_path)
        new_file_contents = file_contents.replace('node1', 'node7')
        DKFileHelper.write_file(graph_file_path, new_file_contents)

        result = runner.invoke(dk, ['file-update',
                                    '--kitchen', test_kitchen,
                                    '--recipe', recipe_name,
                                    '--message', message,
                                    graph_file
                                    ])
        self.assertTrue('node7 does not exist in recipe' in result.output.lower())
        self.assertTrue('unable to update recipe' in result.output.lower())

        # cleanup
        os.chdir(orig_dir)
        runner.invoke(dk, ['kitchen-delete', test_kitchen, '--yes'])
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_recipe(self):
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'cli_test_create_recipe'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'unit-test-my-recipe'
        runner = CliRunner()

        # create test kitchen
        runner.invoke(dk, ['kitchen-delete', test_kitchen, '--yes'])
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, test_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        # make and cd to kitchen dir and get the recipe to disk
        temp_dir = tempfile.mkdtemp(prefix=test_kitchen, dir=TestCommandLine._TEMPFILE_LOCATION)

        # get the new kitchen
        orig_dir = os.getcwd()
        os.chdir(temp_dir)
        result = runner.invoke(dk, ['kitchen-get', test_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        # recipe_create
        time.sleep(20)
        result = runner.invoke(dk, ['recipe-create',
                                    '--kitchen',
                                    test_kitchen,
                                    '--template',
                                    'qs1',
                                    recipe_name])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('created recipe %s' % recipe_name in result.output.lower())

        # recipe_get
        kitchen_dir = os.path.join(temp_dir, test_kitchen)
        os.chdir(kitchen_dir)
        result = runner.invoke(dk, ['recipe-get', recipe_name])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue("Getting the latest version of Recipe '%s' in Kitchen '%s'" % (recipe_name, test_kitchen) in result.output)
        self.assertTrue(DKPathHelper.normalize('%s/resources' % recipe_name, DKPathHelper.WIN) in result.output)

        # show variations
        recipe_dir = os.path.join(kitchen_dir, recipe_name)
        os.chdir(recipe_dir)

        result = runner.invoke(dk, ['recipe-variation-list'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Variations:' in result.output)
        self.assertTrue('Variation1' in result.output)

        # Add email
        file_name = 'variables.json'
        file_path = os.path.join(recipe_dir, file_name)
        contents = DKFileHelper.read_file(file_path)
        DKFileHelper.write_file(file_path, contents.replace('[YOUR EMAIL HERE]', EMAIL))
        contents = DKFileHelper.read_file(file_path)
        self.assertTrue(EMAIL in contents)
        self.assertTrue('[YOUR EMAIL HERE]' not in contents)

        # recipe status
        result = runner.invoke(dk, ['recipe-status'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('1 files are modified on local:' in result.output)
        self.assertTrue('variables.json' in result.output)

        # recipe validate
        result = runner.invoke(dk, ['recipe-validate', '--variation', 'Variation1'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Validating recipe with local changes applied' in result.output)
        self.assertTrue('No recipe issues identified.' in result.output)

        # file-update
        message = 'cli ut file update'
        result = runner.invoke(dk, ['file-update', '--message', message, file_name])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Updating File(s)' in result.output)
        self.assertTrue('update_file for variables.json' in result.output)
        self.assertTrue('succeeded' in result.output)

        # recipe status
        result = runner.invoke(dk, ['recipe-status'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('1 files are modified on local:' not in result.output)
        self.assertTrue('variables.json' not in result.output)

        # file compile
        result = runner.invoke(dk, ['file-compile',
                                    '-v',
                                    'Variation1',
                                    '-f',
                                    'description.json'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('succeeded' in result.output)
        self.assertTrue(EMAIL in result.output)
        self.assertTrue('[YOUR EMAIL HERE]' not in result.output)

        # config list
        result = runner.invoke(dk, ["config-list"])
        self.assertEqual(0, result.exit_code, result.output)
        found_port = False
        found_ip = False
        splitted_output = result.output.split('\n')
        index = 0
        while index < len(splitted_output):
            if not found_port:
                text = 'Cloud Port:'
                start_index_port = splitted_output[index].find(text)
                if start_index_port is not -1:
                    start_index_port += len(text)
                    port = splitted_output[index][start_index_port:].strip('/n').strip()
                    found_port = True
            if not found_ip:
                text = 'Cloud IP:'
                start_index_ip = splitted_output[index].find(text)
                if start_index_ip is not -1:
                    start_index_ip += len(text)
                    ip = splitted_output[index][start_index_ip:].strip('/n').strip()
                    found_ip = True
            index += 1

        self.assertTrue(found_port)
        self.assertTrue(found_ip)

        # file history
        result = runner.invoke(dk, ['file-history',
                                    '-cc',
                                    '5',
                                    'variables.json'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('succeeded' in result.output)
        self.assertTrue('Message:\t%s' % message in result.output)
        self.assertTrue('Message:\tNew recipe %s' % recipe_name in result.output)
        self.assertTrue('Author:' in result.output)
        self.assertTrue('Date:' in result.output)
        self.assertTrue('Url:' in result.output)
        self.assertTrue('%s:%s/dk/index.html#/history/dk/%s/' % (ip, port, test_kitchen))
        self.assertEqual(2,result.output.count('Message:'))

        # modify the file once again
        contents = DKFileHelper.read_file(file_path)
        DKFileHelper.write_file(file_path, contents.replace(EMAIL, 'blah%s' % EMAIL_SUFFIX))
        contents = DKFileHelper.read_file(file_path)
        self.assertTrue('blah%s' % EMAIL_SUFFIX in contents)
        self.assertTrue('[YOUR EMAIL HERE]' not in contents)
        self.assertTrue(EMAIL not in contents)

        # file get
        result = runner.invoke(dk, ['file-get',
                                    'variables.json'])
        print result.output
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Getting File (variables.json)' in result.output)
        self.assertTrue('success' in result.output)
        contents = DKFileHelper.read_file(file_path)
        self.assertTrue('blah%s' % EMAIL_SUFFIX not in contents)
        self.assertTrue('[YOUR EMAIL HERE]' not in contents)
        self.assertTrue(EMAIL in contents)

        # recipe list
        result = runner.invoke(dk, ['recipe-list'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue(recipe_name in result.output)

        # recipe delete
        recipe_sha_dir = os.path.join(kitchen_dir, '.dk', 'recipes', recipe_name)
        self.assertTrue(os.path.exists(recipe_dir))
        self.assertTrue(os.path.exists(recipe_sha_dir))

        os.chdir(kitchen_dir)
        result = runner.invoke(dk, ['recipe-delete', '--yes', recipe_name])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('This command will delete the local and remote copy of recipe' in result.output)
        self.assertTrue('deleted recipe %s' % recipe_name in result.output)

        self.assertFalse(os.path.exists(recipe_dir))
        self.assertFalse(os.path.exists(recipe_sha_dir))

        result = runner.invoke(dk, ['recipe-list'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue(recipe_name not in result.output)

        # cleanup
        os.chdir(orig_dir)
        runner.invoke(dk, ['kitchen-delete', test_kitchen, '--yes'])
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_kitchen_settings(self):
        # setup
        orig_dir = os.getcwd()
        test_kitchen = "master"
        temp_dir = tempfile.mkdtemp(prefix=test_kitchen, dir=TestCommandLine._TEMPFILE_LOCATION)
        os.chdir(temp_dir)
        runner = CliRunner()

        # kitchen-settings-get
        result = runner.invoke(dk, ['kitchen-settings-get'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('succeeded' in result.output)
        self.assertTrue('Find the kitchen-settings.json file in the current directory' in result.output)

        file_name = 'kitchen-settings.json'
        file_path = os.path.join(temp_dir, file_name)
        contents = DKFileHelper.read_file(file_path)
        self.assertTrue('kitchenwizard' in contents)
        self.assertTrue('agile-tools' in contents)

        # backup the original file
        backup_file_name = 'kitchen-settings.json.bkp'
        backup_file_path = os.path.join(temp_dir, backup_file_name)
        copy(file_path, backup_file_path)

        # edit the file
        my_settings = "{\"kitchenwizard\" : {\"wizards\": [], \"variablesets\": []}, \"agile-tools\": null}"
        DKFileHelper.write_file(file_path, my_settings)
        contents = DKFileHelper.read_file(file_path)
        self.assertTrue('variablesets' in contents)

        # kitchen-settings-update
        result = runner.invoke(dk, ['kitchen-settings-update', file_path])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Updating the settings' in result.output)
        self.assertTrue('succeeded' in result.output)

        # restore the file
        copy(backup_file_path, file_path)

        # kitchen-settings-update
        result = runner.invoke(dk, ['kitchen-settings-update', file_path])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Updating the settings' in result.output)
        self.assertTrue('succeeded' in result.output)

        # cleanup
        os.chdir(orig_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_file_top(self):
        # setup
        temp_dir = None
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'CLI-test_delete_file_top'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        recipe_file_key = recipe_name
        file_name = 'description.json'
        message = ' test Delete CLI-test_delete_file_top'
        runner = CliRunner()
        cwd = os.getcwd()
        runner.invoke(dk, ['kitchen-delete', test_kitchen, '--yes'])
        try:
            temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        except Exception as e:
            self.assertTrue(False, 'Problem creating temp folder %s' % e)
        os.chdir(temp_dir)
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, test_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        DKKitchenDisk.write_kitchen(test_kitchen, temp_dir)
        kitchen_dir = os.path.join(temp_dir, test_kitchen)
        os.chdir(kitchen_dir)
        result = runner.invoke(dk, ['file-delete',
                                    '--recipe', recipe_name,
                                    '--message', message,
                                    file_name
                                    ])
        self.assertTrue('ERROR' not in result.output)
        self.assertTrue(self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                       recipe_file_key, file_name, temp_dir) is None, "Found the file")
        runner.invoke(dk, ['kitchen-delete', test_kitchen, '--yes'])
        os.chdir(cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_file_deeper(self):
        # setup
        temp_dir = None
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'CLI-test_delete_file_deeper'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        recipe_file_key = 'resources/very_cool.sql'
        file_name = 'very_cool.sql'
        message = ' test Delete CLI-test_delete_file_deeper'
        runner = CliRunner()
        cwd = os.getcwd()
        runner.invoke(dk, ['kitchen-delete', test_kitchen, '--yes'])
        try:
            temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        except Exception as e:
            self.assertTrue(False, 'Problem creating temp folder %s' % e)
        os.chdir(temp_dir)
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, test_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        DKKitchenDisk.write_kitchen(test_kitchen, temp_dir)
        kitchen_dir = os.path.join(temp_dir, test_kitchen)
        os.chdir(kitchen_dir)

        result = runner.invoke(dk, ['file-delete',
                                    '--recipe', recipe_name,
                                    '--message', message,
                                    recipe_file_key
                                    ])
        self.assertTrue('ERROR' not in result.output)
        self.assertTrue(self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                       os.path.join(recipe_name, recipe_file_key), file_name,
                                                       temp_dir) is None)
        runner.invoke(dk, ['kitchen-delete', '--kitchen', test_kitchen, '--yes'])
        os.chdir(cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_file_deeper_multi(self):
        # setup
        temp_dir = None
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'CLI-test_delete_file_deeper_multi'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        recipe_file_key = 'resources/very_cool.sql'
        file_name = 'very_cool.sql'
        file2 = 'description.json'
        message = ' test Delete CLI-test_delete_file_deeper_multi'
        runner = CliRunner()
        cwd = os.getcwd()
        runner.invoke(dk, ['kitchen-delete', test_kitchen, '--yes'])
        try:
            temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=TestCommandLine._TEMPFILE_LOCATION)
        except Exception as e:
            self.assertTrue(False, 'Problem creating temp folder %s' % e)
        os.chdir(temp_dir)
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, test_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        DKKitchenDisk.write_kitchen(test_kitchen, temp_dir)
        kitchen_dir = os.path.join(temp_dir, test_kitchen)
        os.chdir(kitchen_dir)

        result = runner.invoke(dk, ['file-delete',
                                    '--recipe', recipe_name,
                                    '--message', message,
                                    recipe_file_key,
                                    file2
                                    ])
        self.assertTrue('ERROR' not in result.output)
        self.assertTrue(self._get_recipe_file_contents(runner, test_kitchen, recipe_name,
                                                       os.path.join(recipe_name, recipe_file_key), file_name,
                                                       temp_dir) is None)
        runner.invoke(dk, ['kitchen-delete', '--kitchen', test_kitchen, '--yes'])
        os.chdir(cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_compiled_serving_from_recipe(self):
        # setup
        parent_kitchen = 'master'
        new_kitchen = 'test_get_compiled_serving_from_recipe-API'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe_name = 'parallel-recipe-test'
        variation_name = 'variation-test'
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertEqual(0, result.exit_code, result.output)
        # test
        result = runner.invoke(dk, ['recipe-compile',
                                  '--kitchen', new_kitchen,
                                  '--recipe', recipe_name,
                                  '--variation', variation_name])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue("succeeded, compiled recipe stored in folder 'compiled-recipe'" in result.output)

        # cleanup
        result = runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])
        self.assertEqual(0, result.exit_code, result.output)

    # ------------------------------------------------------------------------------------------------------------------
    #  Order Commands
    # ------------------------------------------------------------------------------------------------------------------

    def test_create_order(self):
        kitchen = 'CLI-Top'
        recipe = 'simple'
        variation = self._get_run_variation_for_recipe(recipe)
        runner = CliRunner()

        # create test kitchen
        result = runner.invoke(dk, ['order-run',
                                    '--kitchen', kitchen,
                                    '--recipe', recipe,
                                    '--yes',
                                    variation])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('simple' in result.output)

    def test_create_order_params(self):
        kitchen = 'master'
        recipe = 'simple-container-recipe'
        variation = "main"
        runner = CliRunner()
        # create test kitchen
        result = runner.invoke(dk, ['order-run',
                                    '--kitchen', kitchen,
                                    '--recipe', recipe,
                                    '--yes',
                                    '--params','{"testvar":"HOLA!!!!"}',
                                    variation])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('simple' in result.output)

    def test_create_order_one_node(self):
        kitchen = 'CLI-Top'
        recipe = 'simple'
        node = 'node2'
        variation = self._get_run_variation_for_recipe(recipe)
        runner = CliRunner()

        # create test kitchen
        result = runner.invoke(dk, ['order-run',
                                    '--kitchen', kitchen,
                                    '--recipe', recipe,
                                    '--node', node,
                                    '--yes',
                                    variation])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('simple' in result.output)

    def test_delete_all_order(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_deleteall_orderCLI'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'simple'
        variation = 'simple-variation-now'
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])  # clean up junk
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertEqual(0, result.exit_code, result.output)
        result = runner.invoke(dk, ['order-run', '--kitchen', new_kitchen, '--recipe', recipe, '--yes', variation])
        self.assertEqual(0, result.exit_code, result.output)
        order_id_raw = result.output
        order_id = order_id_raw.split(':')[1].strip()
        self.assertIsNotNone(variation in order_id)
        # test
        result = runner.invoke(dk, ['order-delete',
                                    '--kitchen',
                                    new_kitchen,
                                    '--yes'])
        self.assertEqual(0, result.exit_code, result.output)
        # cleanup
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])

    def test_delete_one_order(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_deleteall_orderCLI'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'simple'
        variation = 'simple-variation-now'
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])  # clean up junk
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertEqual(0, result.exit_code, result.output)
        result = runner.invoke(dk, ['order-run', '--kitchen', new_kitchen, '--recipe', recipe, '--yes', variation])
        self.assertEqual(0, result.exit_code, result.output)

        order_id_raw = result.output
        text = 'Order ID is: '
        index = order_id_raw.find(text)
        index += len(text)
        order_id = order_id_raw[index:].strip('/n').strip()
        self.assertIsNotNone(variation in order_id)
        # test
        result = runner.invoke(dk, ['order-delete',
                                    '--kitchen',
                                    new_kitchen,
                                    '--order_id',
                                    order_id,
                                    '--yes'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('deleted order %s' % order_id in result.output)
        # cleanup
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])

    def test_order_stop(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'stop-da-order-CLI'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'test-everything-recipe'
        variation = 'variation-morning-prod05'
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])  # clean up junk
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertEqual(0, result.exit_code, result.output)
        result = runner.invoke(dk, ['order-run', '--kitchen', new_kitchen, '--recipe', recipe, '--yes', variation])
        self.assertEqual(0, result.exit_code, result.output)
        order_id_raw = result.output
        text = 'Order ID is: '
        index = order_id_raw.find(text)
        index += len(text)
        order_id = order_id_raw[index:].strip('/n').strip()
        # test
        time.sleep(2)

        result_stop = runner.invoke(dk, ['order-stop',
                                         '--kitchen',
                                         new_kitchen,
                                         '--order_id',
                                         order_id,
                                         '--yes'])
        self.assertEqual(0,int(result_stop.exit_code),result_stop.output)
        self.assertTrue('stopped order %s' % order_id in result_stop.output)

        # cleanup
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])

    def test_delete_order_bad_order_id(self):
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'delete_order_bad_order_id-CLI'
        new_kitchen = self._add_my_guid(new_kitchen)
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])  # clean up junk
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        order_id = 'junk'
        runner = CliRunner()
        result = runner.invoke(dk, ['order-delete',
                                    '--kitchen',
                                    new_kitchen,
                                    '--order_id',
                                    order_id,
                                    '--yes'])
        self.assertNotEqual(0,result.exit_code,result.output)
        self.assertTrue('Could not delete the Order.' in result.output)
        self.assertTrue('Order id \'junk\' does not exist.' in result.output)

    def test_delete_order_bad_kitchen(self):
        kitchen = 'junk'
        runner = CliRunner()
        result = runner.invoke(dk, ['order-delete',
                                    '--kitchen', 
                                    kitchen,
                                    '--yes'])
        self.assertNotEqual(0, result.exit_code, result.output)
        message = 'Kitchen %s was not found in the database or the user does not have access rights.' % kitchen
        self.assertTrue(message in result.output)

    # test illegal command line combo
    def test_orderrun_detail_bad_command(self):
        kitchen = 'ppp'
        runner = CliRunner()
        result = runner.invoke(dk, ['orderrun-info',
                                    '--kitchen', kitchen,
                                    '-o', 'o', '-r', 'r'])
        self.assertNotEqual(0,result.exit_code,result.output)
        self.assertTrue('Error' in result.output)

    def test_list_order(self):
        kitchen = 'CLI-Top'
        runner = CliRunner()
        result = runner.invoke(dk, ['order-list', '--kitchen', kitchen])
        self.assertEqual(0, result.exit_code, result.output)

    def test_list_order_filter_recipe(self):
        kitchen = 'CLI-Top'
        recipe1 = 'simple'
        recipe2 = 's3-small-recipe'
        runner = CliRunner()

        result = runner.invoke(dk, ['order-list', '--kitchen', kitchen, '--recipe', recipe1])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Get Order information for Kitchen %s' % kitchen in result.output)
        self.assertTrue(recipe2 not in result.output)

        result = runner.invoke(dk, ['order-list', '--kitchen', kitchen, '--recipe', recipe2])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Get Order information for Kitchen %s' % kitchen in result.output)
        self.assertTrue(recipe1 not in result.output)

    def test_list_order_paging(self):
        kitchen = 'CLI-Top'
        runner = CliRunner()

        result = runner.invoke(dk, ['order-list', '--kitchen', kitchen])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Get Order information for Kitchen %s' % kitchen in result.output)
        count_paging_default = result.output.count('ORDER SUMMARY')
        self.assertEqual(5,count_paging_default)

        result = runner.invoke(dk, ['order-list',
                                    '--kitchen', kitchen,
                                    '--start', 2,
                                    '--order_count', 1,
                                    '--order_run_count', 1])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Get Order information for Kitchen %s' % kitchen in result.output)
        count_paging = result.output.count('ORDER SUMMARY')
        self.assertEqual(1,count_paging)

    def test_orderrun_stop(self):
        parent_kitchen = 'CLI-Top'
        recipe_name = 'parallel-recipe-test'
        variation_name = self._get_run_variation_for_recipe(recipe_name)
        new_kitchen = 'test_orderrun_stop-CLI'
        new_kitchen = self._add_my_guid(new_kitchen)
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        # start order & order run
        print 'Starting Create-Order in test_orderrun_stop()'
        result = runner.invoke(dk, ['order-run',
                                    '--kitchen', new_kitchen,
                                    '--recipe', recipe_name,
                                    '--yes',
                                    variation_name])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Order ID is:' in result.output)

        order_id_raw = result.output
        text = 'Order ID is: '
        index = order_id_raw.find(text)
        index += len(text)
        order_id = order_id_raw[index:].strip('/n').strip()

        wait_time = [.5] * 20 + [1] * 10 + [2] * 10 + [5] * 10
        
        found_active_serving = False
        for wt in wait_time:
            time.sleep(wt)
            resp1 = runner.invoke(dk, ['orderrun-info', '-k', new_kitchen, '-o', order_id])
            if resp1.output is not None:
                if "ACTIVE_SERVING" in resp1.output or "PLANNED_SERVING" in resp1.output:
                    found_active_serving = True

                    order_run_id_raw = resp1.output
                    text = 'Order Run ID:'
                    index = order_run_id_raw.find(text)
                    index += len(text)
                    text2 = 'Status:'
                    index2 = order_run_id_raw.find(text2)
                    order_run_id = order_run_id_raw[index:index2].strip('/n').strip()
                    break

        self.assertTrue(found_active_serving)
        print 'test_orderrun_stop: found_active_serving is True'

        resp3 = runner.invoke(dk, ['orderrun-stop', '-k', new_kitchen, '-ori', order_run_id, '--yes'])
        self.assertEqual(0,resp3.exit_code,resp3.output)
        self.assertTrue('stopped order run %s' % order_run_id in resp3.output)

        # check to make sure the serving is in the "STOPPED_SERVING" state
        found_stopped_state = False
        for wt in wait_time:
            time.sleep(wt)
            resp4 = runner.invoke(dk, ['orderrun-info', '-k', new_kitchen, '-ori', order_run_id, '--runstatus'])
            if resp4.output is not None:
                self.assertFalse('Current context is:' in resp4.output)
                print '(%i) got %s' % (wt, resp4.output)
                if "STOPPED_SERVING" in resp4.output:
                    found_stopped_state = True
                    break
        print 'test_orderrun_stop: found_stopped_state is True'
        self.assertTrue(found_stopped_state)

        # cleanup
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])

    def test_orderrun_resume(self):
        parent_kitchen = 'CLI-Top'
        recipe_name = 'unit-test-order-resume'
        variation_name = 'Variation1'
        new_kitchen = 'test_orderrun_resume-CLI'
        new_kitchen = self._add_my_guid(new_kitchen)
        runner = CliRunner()

        # Delete kitchen i already existing
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])

        # Create Kitchen
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        # Start order & order run
        print 'Starting Create-Order in test_orderrun_resume()'
        result = runner.invoke(dk, ['order-run',
                                    '--kitchen', new_kitchen,
                                    '--recipe', recipe_name,
                                    '--yes',
                                    variation_name])
        self.assertEqual(0, result.exit_code, result.output)
        order_id_raw = result.output
        text = 'Order ID is: '
        index = order_id_raw.find(text)
        index += len(text)
        order_id = order_id_raw[index:].strip('/n').strip()

        # Wait for state "SERVING_ERROR"
        wait_time = [.1, 1, 1, 2, 2, 2, 4, 4, 4, 4, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        desired_state = 'SERVING_ERROR'
        found_desired_serving_state = False
        wait_generator = (wt for wt in wait_time if found_desired_serving_state is False)
        for wt in wait_generator:
            time.sleep(wt)
            resp1 = runner.invoke(dk, ['orderrun-info',
                                       '-k', new_kitchen,
                                       '-o', order_id])
            if resp1.output is not None:
                print '(%i) got %s' % (wt, resp1.output)
                if desired_state in resp1.output:
                    found_desired_serving_state = True
                    text = 'Order Run ID:'
                    index = resp1.output.find(text)
                    index += len(text)
                    text2 = 'Status:'
                    index2 = resp1.output.find(text2)
                    orderrun_id = resp1.output[index:index2].strip('/n').strip()
                    orderrun_id_error = orderrun_id
        self.assertTrue(found_desired_serving_state)
        print 'test_orderrun_resume: found error in serving'

        # Make temp location
        temp_dir = tempfile.mkdtemp(prefix=new_kitchen, dir=TestCommandLine._TEMPFILE_LOCATION)

        orig_dir = os.getcwd()
        os.chdir(temp_dir)

        # Get the kitchen
        result = runner.invoke(dk, ['kitchen-get', new_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        # Get the recipe
        kitchen_dir = os.path.join(temp_dir, new_kitchen)
        os.chdir(kitchen_dir)
        result = runner.invoke(dk, ['recipe-get', recipe_name])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue("Getting the latest version of Recipe '%s' in Kitchen '%s'" % (recipe_name, new_kitchen) in result.output)
        self.assertTrue(DKPathHelper.normalize('%s/resources' % recipe_name, DKPathHelper.WIN) in result.output)

        # Fix the recipe error
        recipe_dir = os.path.join(kitchen_dir, recipe_name)
        file_name = DKPathHelper.normalize('resources/s3-to-redshift.sql', DKPathHelper.WIN)
        file_path = os.path.join(recipe_dir, file_name)
        contents = DKFileHelper.read_file(file_path)
        DKFileHelper.write_file(file_path, contents.replace('make this sql fail', '-- fix this sql'))
        contents = DKFileHelper.read_file(file_path)
        self.assertTrue('-- fix this sql' in contents)

        # file-update
        os.chdir(recipe_dir)
        message = 'cli ut file update'
        result = runner.invoke(dk, ['file-update', '--message', message, file_name])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Updating File(s)' in result.output)
        self.assertTrue('update_file for %s' % file_name in result.output)
        self.assertTrue('succeeded' in result.output)

        # recipe status
        result = runner.invoke(dk, ['recipe-status'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('files are modified on local:' not in result.output)
        self.assertTrue('13 files are unchanged' in result.output)

        # Resume the recipe
        result = runner.invoke(dk, ['orderrun-resume',
                                    '--kitchen',
                                    new_kitchen,
                                    orderrun_id,
                                    '--yes'])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Resuming Order-Run %s' % orderrun_id in result.output)
        self.assertTrue('succeeded' in result.output)

        # Check now is successful, wait for state "COMPLETED_SERVING"
        wait_time = [.1, 1, 1, 2, 2, 2, 4, 4, 4, 4, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        desired_state = 'COMPLETED_SERVING'
        found_desired_serving_state = False
        wait_generator = (wt for wt in wait_time if found_desired_serving_state is False)
        for wt in wait_generator:
            time.sleep(wt)
            resp1 = runner.invoke(dk, ['orderrun-info',
                                       '-k', new_kitchen])
            if resp1.output is not None:
                print '(%i) got %s' % (wt, resp1.output)
                if desired_state in resp1.output:
                    text = 'Order Run ID:'
                    index = resp1.output.find(text)
                    index += len(text)
                    text2 = 'Status:'
                    index2 = resp1.output.find(text2)
                    orderrun_id_success = resp1.output[index:index2].strip('/n').strip()
                    found_desired_serving_state = True
        self.assertTrue(found_desired_serving_state)
        print 'test_orderrun_resume: found completed serving in serving'

        # Check order runs by order run id
        self._check_order_run_info_by_ori(new_kitchen, orderrun_id_error, 'SERVING_RERAN')
        self._check_order_run_info_by_ori(new_kitchen, orderrun_id_success, 'COMPLETED_SERVING')

        # cleanup
        os.chdir(orig_dir)
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])

    def test_wait_for_serving_states(self):
        # setup
        parent_kitchen = 'CLI-Top'
        recipe_name = 'parallel-recipe-test'
        variation_name = self._get_run_variation_for_recipe(recipe_name)
        new_kitchen = 'test_scenario_orderrun_stop-CLI'
        new_kitchen = self._add_my_guid(new_kitchen)
        runner = CliRunner()
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])
        time.sleep(TestCommandLine.SLEEP_TIME)
        result = runner.invoke(dk, ['kitchen-create', '--parent', parent_kitchen, new_kitchen])
        self.assertEqual(0, result.exit_code, result.output)

        # start order & order run
        print 'Starting Create-Order in test_scenario_orderrun_stop()'
        result = runner.invoke(dk, ['order-run',
                                    '--kitchen', new_kitchen,
                                    '--recipe', recipe_name,
                                    '--yes',
                                    variation_name])
        self.assertEqual(0, result.exit_code, result.output)
        order_id_raw = result.output
        order_id = order_id_raw.split(':')[1].strip()
        self.assertIsNotNone(variation_name in order_id)
        wait_time = [.1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

        # wait for state "ACTIVE_SERVING"
        # not going to try for "PLANNED_SERVING" because that may go by too fast
        found_active_serving = False
        wait_generator = (wt for wt in wait_time if found_active_serving is False)
        for wt in wait_generator:
            time.sleep(wt)
            resp1 = runner.invoke(dk, ['orderrun-info', '-k', new_kitchen, '--runstatus'])
            if resp1.output is not None:
                self.assertFalse('Current context is:' in resp1.output)
                print '(%i) got %s' % (wt, resp1.output)
                if "ACTIVE_SERVING" in resp1.output:
                    found_active_serving = True
        self.assertTrue(found_active_serving)
        print 'test_scenario_orderrun_stop: found_active_serving is True'

        # wait for state "COMPLETED_SERVING"
        found_completed_serving = False
        wait_generator = (wt for wt in wait_time if found_completed_serving is False)
        for wt in wait_generator:
            time.sleep(wt)
            resp2 = runner.invoke(dk, ['orderrun-info', '-k', new_kitchen, '--runstatus'])
            if resp2.output is not None:
                self.assertFalse('Current context is:' in resp2.output)
                print '(%i) got %s' % (wt, resp2.output)
                if "COMPLETED_SERVING" in resp2.output:
                    found_completed_serving = True
        self.assertTrue(found_completed_serving)
        print 'test_scenario_orderrun_stop: found_completed_serving is True'

        # Full dk ori -at command check
        self._check_order_run_info_all_things(new_kitchen, recipe=recipe_name, variation=variation_name,
                                              status='COMPLETED_SERVING')

        # cleanup
        runner.invoke(dk, ['kitchen-delete', new_kitchen, '--yes'])

    # ------------------------------------------------------------------------------------------------------------------
    #  Secret Commands
    # ------------------------------------------------------------------------------------------------------------------

    def test_secrets(self):
        runner = CliRunner()

        result = runner.invoke(dk, ["secret-write", "cli-unit-tests/value='hello'", "--yes"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Secret written.' in result.output)

        result = runner.invoke(dk, ["secret-list"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Getting the list of secrets' in result.output)
        print result.output
        self.assertTrue('s3_schema/' in result.output)
        self.assertTrue('cli-unit-tests/' in result.output)

        result = runner.invoke(dk, ["secret-list", "-rc"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Getting the list of secrets' in result.output)
        self.assertTrue('vault://cli-unit-tests/value' in result.output)

        result = runner.invoke(dk, ["secret-exists", "cli-unit-tests/value"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('True' in result.output)

        result = runner.invoke(dk, ["secret-delete", "cli-unit-tests/value", "--yes"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Secret deleted.' in result.output)

        result = runner.invoke(dk, ["secret-list"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Getting the list of secrets' in result.output)
        self.assertTrue('s3_schema/' in result.output)
        self.assertTrue('cli-unit-tests/' not in result.output)

        result = runner.invoke(dk, ["secret-list", "-rc"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Getting the list of secrets' in result.output)
        self.assertTrue('vault://cli-unit-tests/value' not in result.output)

        result = runner.invoke(dk, ["secret-exists", "cli-unit-tests/value"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('False' in result.output)

    def test_agent_status(self):
        runner = CliRunner()
        result = runner.invoke(dk, ["agent-status"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue('Agent is Online' in result.output)
        self.assertTrue('Total available memory:' in result.output)
        self.assertTrue('Total available disk space:' in result.output)

    # ---------------------------------------------- helpers -----------------------------------------------------------
    def _check_no_merge_conflicts(self, resp):
        self.assertTrue(str(resp).find('diverged') < 0)

    def _get_recipe_file_contents(self, runner, kitchen, recipe_name, recipe_file_key, file_name, temp_dir=None):
        delete_temp_dir = False
        if temp_dir is None:
            td = tempfile.mkdtemp(prefix='unit-tests-grfc', dir=TestCommandLine._TEMPFILE_LOCATION)
            delete_temp_dir = True
            DKKitchenDisk.write_kitchen(kitchen, td)
            kitchen_directory = os.path.join(td, kitchen)
        else:
            td = temp_dir
            kitchen_directory = os.getcwd()
        cwd = os.getcwd()
        os.chdir(kitchen_directory)
        result = runner.invoke(dk, ['recipe-get', recipe_name])
        os.chdir(cwd)
        rv = result.output
        self.assertTrue(recipe_name in rv)
        abspath = os.path.join(td, os.path.join(kitchen, recipe_file_key, file_name))
        if os.path.isfile(abspath):
            with open(abspath, 'r') as rfile:
                rfile.seek(0)
                the_file = rfile.read()
            rc = the_file
        else:
            rc = None
        if delete_temp_dir is True:
            shutil.rmtree(td, ignore_errors=True)
        return rc

    def _get_recipe(self, runner, recipe):
        result = runner.invoke(dk, ['recipe-get', recipe])
        rv = result.output
        self.assertTrue(recipe in rv)
        return True

    def _check_order_run_info_by_ori(self, kitchen, orderrun_id, expected_status):
        runner = CliRunner()
        result = runner.invoke(dk, ['orderrun-info', '-k', kitchen, '-ori', orderrun_id])
        self.assertEqual(0, result.exit_code, result.output)

        splitted_output = result.output.split('\n')
        index = 0
        stage = 1
        while index < len(splitted_output):
            if stage == 1:
                if 'ORDER RUN SUMMARY' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 2:
                if 'Order ID:' in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 3:
                if 'Order Run ID:' in splitted_output[index] and orderrun_id in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 4:
                if 'Status:' in splitted_output[index] and expected_status in splitted_output[index]: stage += 1
                index += 1
                continue
            if stage == 5:
                if 'Run duration:' in splitted_output[index]: stage += 1
                index += 1
                continue
            index += 1
        self.assertEqual(6,stage)

    def _check_order_run_info_all_things(self, kitchen, recipe=None, variation=None, status=None, order_id=None, order_run_id=None):
        runner = CliRunner()
        result = runner.invoke(dk, ['orderrun-info', '-k', kitchen, '-at'])
        self.assertEqual(0, result.exit_code, result.output)

        current_year = datetime.datetime.now().year
        
        conditions = [
            'ORDER RUN SUMMARY',
            'Order ID:\t%s' % (order_id if order_id is not None else ''),
            'Order Run ID:\t%s' % (order_run_id if order_run_id is not None else ''),
            'Status:\t\t%s' % (status if status is not None else ''),
            'Kitchen:\t%s' % kitchen,
            'Recipe:\t\t%s' % (recipe if recipe is not None else ''),
            'Variation:\t%s' % (variation if variation is not None else ''),
            'Start time:\t%s-' % current_year,
            'Run duration:\t0:',
            'TEST RESULTS',
            'Tests: Failed',
            'Tests: Warning',
            'Tests: Log',
            'Tests: Passed',
            'TIMING RESULTS',
            'DKRecipe timing (parallel-recipe-test), status = DKNodeStatus_completed_production',
            'total recipe execution time|0:',
            'Node (node9), status = DKNodeStatus_completed_production, timing is||0:0',
            '(node9) Data Source(noopsource) timing is||0:0',
            '(node9) Notebook elapsed time is|0:0',
            '(node9) Data Sink(noopsink) timing is||None',
            'STEP STATUS',
            'node1\tDKNodeStatus_completed_production',
            'node2\tDKNodeStatus_completed_production',
            'node3\tDKNodeStatus_completed_production',
            'node4\tDKNodeStatus_completed_production',
            'node5\tDKNodeStatus_completed_production',
            'node6\tDKNodeStatus_completed_production',
            'node7\tDKNodeStatus_completed_production',
            'node8\tDKNodeStatus_completed_production',
            'node9\tDKNodeStatus_completed_production',
            'LOG',
            'Log Format:\t\tdatetime | record_type | thread_name | message',
            ' | INFO | MainThread | DKCommandServer: starting',
            ' | INFO | MainThread | DKCommandServer in kitchen: %s' % kitchen,
            ' | INFO | NodeConsumerThread#1 | Set node in production',
            ' | INFO | VariationThread | Ending variation make thread'
        ]
        
        for condition in conditions:
            self.assertTrue(condition in result.output)


if __name__ == '__main__':
    unittest.main()
