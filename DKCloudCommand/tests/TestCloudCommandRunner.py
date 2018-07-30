# coding=utf-8
import re
import unittest
import datetime, time
import tempfile
import pickle
from sys import path, stdout
import os
import shutil
import uuid
from os.path import expanduser

from BaseTestCloud import BaseTestCloud
from DKCloudCommandRunner import DKCloudCommandRunner
from DKActiveServingWatcher import *
from DKCloudAPIMock import DKCloudAPIMock
from DKFileHelper import DKFileHelper
from DKPathHelper import DKPathHelper
from DKRecipeDisk import DKRecipeDisk

from DKModules.DKJSONParser import DKJSONParser

from githash import *


class TestCloudCommandRunner(BaseTestCloud):

    def setUp(self):
        super(TestCloudCommandRunner, self).setUp()
        self._kitchens = list()
        self._tmpdirs = list()

    def tearDown(self):
        for kitchen in self._kitchens:
            print "delete kitchen %s" % kitchen
            self._delete_and_clean_kitchen(kitchen)
        for tmpdir in self._tmpdirs:
            print "delete tmp dir %s" % tmpdir
            shutil.rmtree(tmpdir, ignore_errors=True)
        super(TestCloudCommandRunner, self).tearDown()

    def test_rude(self):
        tv = 'DKCloudCommand.rude = **rude**\n'
        rv = DKCloudCommandRunner.rude(self._api)
        self.assertIsNotNone(rv)
        self.assertEqual(rv, tv)

        rv = DKCloudCommandRunner.rude(BaseTestCloud)
        self.assertIn('ERROR', rv)

    def test_a_list_kitchens(self):
        tv1 = 'CLI-Top'
        tv2 = 'kitchens-plus'
        tv3 = 'master'
        # tv = 'DKCloudCommand.kitchens returned 3 kitchens\n  base-test-kitchen \n  kitchens-plus \n  master \n'
        rc = DKCloudCommandRunner.list_kitchen(self._api)
        self.assertTrue(rc.ok())
        rv = rc.get_message()
        self.assertTrue(isinstance(rv, basestring))
        self.assertTrue(tv1 in rv)
        self.assertTrue(tv2 in rv)
        self.assertTrue(tv3 in rv)

    def test_get_kitchen(self):
        tk = 'CLI-Top'

        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=self._TEMPFILE_LOCATION)

        kitchen_path = os.path.join(temp_dir, tk)
        os.makedirs(kitchen_path)

        # kitchen dir already has a folder in it.
        bad_path = os.path.join(kitchen_path, 'bad')
        os.makedirs(bad_path)
        rv = DKCloudCommandRunner.get_kitchen(self._api, tk, temp_dir)
        self.assertFalse(rv.ok())
        shutil.rmtree(bad_path, ignore_errors=True)

        # kitchen dir already has a file in it.
        with open(os.path.join(kitchen_path, 'bad.txt'), 'w') as bad_file:
            bad_file.write('bad.txt')
        rv = DKCloudCommandRunner.get_kitchen(self._api, tk, temp_dir)
        self.assertFalse(rv.ok())
        shutil.rmtree(kitchen_path, ignore_errors=True)

        # kitchen dir exists, but is empty
        kitchen_path = os.path.join(temp_dir, tk)
        os.makedirs(kitchen_path)
        rv = DKCloudCommandRunner.get_kitchen(self._api, tk, temp_dir)
        self.assertTrue(rv.ok())
        self.assertEqual(os.path.isdir(os.path.join(kitchen_path, '.dk')), True)
        shutil.rmtree(kitchen_path, ignore_errors=True)

        # kitchen dir does not exists.
        rv = DKCloudCommandRunner.get_kitchen(self._api, tk, temp_dir)
        self.assertTrue(rv.ok())
        self.assertEqual(os.path.isdir(os.path.join(kitchen_path, '.dk')), True)

        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_which_kitchen(self):
        temp_dir = tempfile.mkdtemp(prefix='unit-tests', dir=self._TEMPFILE_LOCATION)
        kn = 'fake'
        kp = os.path.join(temp_dir, kn)
        os.makedirs(kp)
        dk = os.path.join(kp, '.dk')
        os.makedirs(dk)
        with open(os.path.join(dk, 'KITCHEN_META'), 'w') as meta:
            meta.write(kn)

        rv = DKCloudCommandRunner.which_kitchen(self._api, path=kp)
        self.assertIn('You are in', rv.get_message())

        rv = DKCloudCommandRunner.which_kitchen(self._api, kp)
        self.assertIn('You are in', rv.get_message())

        rv = DKCloudCommandRunner.which_kitchen(temp_dir)
        self.assertFalse(rv.ok())


    def test_create_kitchen(self):
        parent = 'CLI-Top'
        kitchen = 'temp-create-kitchen-Runner'
        kitchen = self._add_my_guid(kitchen)

        rv = DKCloudCommandRunner.delete_kitchen(self._api, kitchen)
        self.assertIsNotNone(rv)

        rv = DKCloudCommandRunner.create_kitchen(self._api, parent, kitchen)
        self.assertTrue(rv.ok())
        self.assertEquals('success', rv.rc['status'])
        self.assertTrue('There are recipe overrides at the parent kitchen, which were copied onto the new kitchen:' in rv.rc['message'])
        self.assertTrue('Variable: var-name' in rv.rc['message'])

        rc = DKCloudCommandRunner.list_kitchen(self._api)
        rv2 = rc.get_message()
        self.assertTrue(kitchen in rv2)

        # cleanup
        rv = DKCloudCommandRunner.delete_kitchen(self._api, kitchen)
        self.assertIsNotNone(rv)

    def test_delete_kitchen(self):
        parent = 'CLI-Top'
        kitchen = 'temp-delete-kitchen-Runner'
        kitchen = self._add_my_guid(kitchen)
        rv = DKCloudCommandRunner.delete_kitchen(self._api, kitchen)
        self.assertIsNotNone(rv)

        rv = DKCloudCommandRunner.create_kitchen(self._api, parent, kitchen)
        self.assertTrue(rv.ok())

        rv = DKCloudCommandRunner.delete_kitchen(self._api, kitchen)
        self.assertTrue(rv.ok())
        rc = DKCloudCommandRunner.list_kitchen(self._api)
        rv2 = rc.get_message()
        self.assertTrue(kitchen not in rv2)

    def test_recipe_list(self):
        tv1 = 's3-small-recipe'
        tv2 = 'simple'
        tv3 = 'parallel-recipe-test'
        rc = DKCloudCommandRunner.list_recipe(self._api, 'CLI-Top')
        rv = rc.get_message()
        self.assertTrue(tv1 in rv)
        self.assertTrue(tv2 in rv)
        self.assertTrue(tv3 in rv)

    def test_binary_files(self):
        existing_kitchen_name = 'CLI-Top'
        recipe_name = 'simple-binary'
        kitchen_name = self._add_my_guid('test_binary_files')

        # setup
        self._delete_and_clean_kitchen(kitchen_name)
        orig_dir = os.getcwd()

        # create kitchen
        rs = DKCloudCommandRunner.create_kitchen(self._api, existing_kitchen_name, kitchen_name)
        self.assertTrue(rs.ok())

        # get recipe to disk
        temp_dir, recipe_dir = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # test binary files are present
        book1_full_path = os.path.join(recipe_dir, 'resources', 'excel', 'Book1.xlsx')
        book2_full_path = os.path.join(recipe_dir, 'resources', 'excel', 'Book2.xlsx')
        self.assertTrue(os.path.isfile(book1_full_path))
        self.assertTrue(os.path.isfile(book2_full_path))

        # recipe-status should list no changes
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertTrue(rs.ok())
        self.assertTrue('26 files are unchanged' in rs.get_message())

        # simulate adding a binary file
        book3_full_path = os.path.join(recipe_dir, 'resources', 'excel', 'Book3.xlsx')
        book3_recipe_path = os.path.join('resources', 'excel', 'Book3.xlsx')
        shutil.copy2(book1_full_path, book3_full_path)
        self.assertTrue(os.path.isfile(book3_full_path))

        # recipe-status should list local changes
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertTrue(rs.ok())
        expected_result = ('1 files are local only:\n'
                           '	resources/excel/Book3.xlsx\n')
        self.assertTrue(DKPathHelper.normalize(expected_result, DKPathHelper.WIN) in rs.get_message())

        # file add
        os.chdir(recipe_dir)
        message = 'unit test binary file update'
        rs = DKCloudCommandRunner.update_file(self._api, kitchen_name, recipe_name, recipe_dir, message, book3_recipe_path)
        self.assertTrue(rs.ok())

        # recipe-status should list no changes
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertTrue(rs.ok())
        self.assertTrue('27 files are unchanged' in rs.get_message())
        self.assertTrue(os.path.isfile(book3_full_path))

        # simulate adding a binary file
        book4_full_path = os.path.join(recipe_dir, 'resources', 'excel', 'Book4.xlsx')
        book4_recipe_path = os.path.join('resources', 'excel', 'Book4.xlsx')
        shutil.copy2(book1_full_path, book4_full_path)
        self.assertTrue(os.path.isfile(book4_full_path))

        # recipe-status should list local changes
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertTrue(rs.ok())
        expected_result = ('1 files are local only:\n'
                           '	resources/excel/Book4.xlsx\n')
        self.assertTrue(DKPathHelper.normalize(expected_result, DKPathHelper.WIN) in rs.get_message())

        # file update
        message = 'unit test binary file update'
        rs = DKCloudCommandRunner.update_file(self._api, kitchen_name, recipe_name, recipe_dir, message, book4_recipe_path)
        self.assertTrue(rs.ok())

        # recipe-status should list no changes
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertTrue(rs.ok())
        self.assertTrue('28 files are unchanged' in rs.get_message())
        self.assertTrue(os.path.isfile(book4_full_path))

        # simulate adding a binary file
        book5_full_path = os.path.join(recipe_dir, 'resources', 'excel', 'Book5.xlsx')
        book5_recipe_path = os.path.join('resources', 'excel', 'Book5.xlsx')
        shutil.copy2(book1_full_path, book5_full_path)
        self.assertTrue(os.path.isfile(book5_full_path))

        # recipe-status should list local changes
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertTrue(rs.ok())
        expected_result = ('1 files are local only:\n'
                           '	resources/excel/Book5.xlsx\n')
        self.assertTrue(DKPathHelper.normalize(expected_result, DKPathHelper.WIN) in rs.get_message())

        # recipe update
        message = 'unit test binary file update'
        rc = DKCloudCommandRunner.update_all_files(self._api, kitchen_name, recipe_name, recipe_dir, message)
        self.assertTrue(rc.ok())
        expected_result = ('Update results:\n\n'
                           'New files:'
                           '\n\tresources/excel/Book5.xlsx\n'
                           'Updated files:'
                           '\n\tNone\n'
                           'Deleted files:'
                           '\n\tNone\n\n'
                           'Issues:\n\nNo issues found')

        self.assertTrue(DKPathHelper.normalize(expected_result, DKPathHelper.WIN) in rc.get_message())

        # recipe-status should list no changes
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertTrue(rs.ok())
        self.assertTrue('29 files are unchanged' in rs.get_message())
        self.assertTrue(os.path.isfile(book4_full_path))

        # intentionally remove a file
        os.remove(book3_full_path)
        self.assertFalse(os.path.isfile(book3_full_path))

        # file get
        rs = DKCloudCommandRunner.get_file(self._api, kitchen_name, recipe_name, book3_recipe_path)
        self.assertTrue(rs.ok())
        self.assertTrue(os.path.isfile(book3_full_path))

        # cleanup
        os.chdir(orig_dir)
        rv = DKCloudCommandRunner.delete_kitchen(self._api, kitchen_name)
        self.assertIsNotNone(rv)

    def test_recipe_update(self):
        existing_kitchen_name = 'CLI-Top'
        recipe_name = 'simple'
        kitchen_name = self._add_my_guid('test_recipe_update')

        # setup
        self._delete_and_clean_kitchen(kitchen_name)
        orig_dir = os.getcwd()

        # create kitchen
        rs = DKCloudCommandRunner.create_kitchen(self._api, existing_kitchen_name, kitchen_name)
        self.assertTrue(rs.ok())

        # get recipe to disk
        temp_dir, recipe_dir = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # create a new dir
        os.chdir(os.path.join(recipe_dir, 'node1'))
        os.mkdir('subdir')
        os.chdir(os.path.join(recipe_dir, 'node1', 'subdir'))
        os.mkdir('subdir2a')
        os.mkdir('subdir2b')
        os.chdir(orig_dir)

        # add a new file in local
        local_new_file_path = os.path.join(recipe_dir, os.path.normpath('node1/subdir/subdir2a/local_new_file.json'))
        with open(local_new_file_path, 'w') as f:
            f.write('This is my new file. Hooray!')

        # recipe-status should list local changes
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        expected_result = ('1 files are local only:\n'
                           '	node1/subdir/subdir2a/local_new_file.json\n')
        self.assertTrue(DKPathHelper.normalize(expected_result, DKPathHelper.WIN) in rs.get_message())

        # recipe update
        message = 'test updating the recipe with one new file'
        rs = DKCloudCommandRunner.update_all_files(self._api, kitchen_name, recipe_name, recipe_dir, message)
        self.assertTrue(rs.ok())
        self.assertFalse(recipe_dir in rs.get_message())

        # cleanup
        rv = DKCloudCommandRunner.delete_kitchen(self._api, kitchen_name)
        self.assertIsNotNone(rv)

    def test_recipe_status_sha_encoding(self):
        existing_kitchen_name = 'CLI-Top'
        recipe_name = 'simple-encoding'
        kitchen_name = self._add_my_guid('test_recipe_status_sha_encoding')

        # setup
        self._delete_and_clean_kitchen(kitchen_name)

        # create kitchen
        rs = DKCloudCommandRunner.create_kitchen(self._api, existing_kitchen_name, kitchen_name)
        self.assertTrue(rs.ok())

        # get recipe to disk
        temp_dir, recipe_dir = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # recipe-status should show no changes
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertTrue(rs.ok())
        expected_result = '11 files are unchanged'
        self.assertTrue(expected_result in rs.get_message())
        self.assertEquals(0, len(rs.get_payload()['different']))
        self.assertEquals(0, len(rs.get_payload()['local_and_remote_modified']))
        self.assertEquals(0, len(rs.get_payload()['local_modified']))
        self.assertEquals(0, len(rs.get_payload()['non_local_modified']))
        self.assertEquals(0, len(rs.get_payload()['only_local']))
        self.assertEquals(0, len(rs.get_payload()['only_remote']))
        self.assertEquals(0, len(rs.get_payload()['only_remote_dir']))
        self.assertEquals(0, len(rs.get_payload()['remote_modified']))
        self.assertEquals(5, len(rs.get_payload()['same']))

        # cleanup
        rv = DKCloudCommandRunner.delete_kitchen(self._api, kitchen_name)
        self.assertIsNotNone(rv)

    def test_recipe_get_new(self):
        kitchen_name = 'CLI-Top'
        recipe_name = 'simple'
        temp_dir, kitchen_dir = self._make_kitchen_dir(kitchen_name, change_dir=True)
        rv = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name)
        self.assertTrue(recipe_name in rv.get_message())
        self.assertTrue('sections' in rv.get_message())
        recipe_dir = os.path.join(kitchen_dir, recipe_name)
        self.assertTrue(os.path.exists(recipe_dir))
        total_files = get_total_files(recipe_dir)
        self.assertTrue(total_files > 15)

        # check FILE_SHA exists
        recipe_meta_dir = os.path.join(kitchen_dir, '.dk', 'recipes', recipe_name)
        self.assertTrue(os.path.exists(recipe_meta_dir))
        file_sha = DKFileHelper.read_file(os.path.join(recipe_meta_dir, 'FILE_SHA'))
        for line in file_sha.splitlines():
            file_name, file_sha = line.split(':')
            self.assertTrue(file_name.startswith(recipe_name))
            self.assertEqual(40, len(file_sha))

        # check ORIG_HEAD exists
        orig_head = DKFileHelper.read_file(os.path.join(recipe_meta_dir, 'ORIG_HEAD'))
        self.assertTrue(len(orig_head.strip()) > 0)

        # recipe status should return "files are unchanged"
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertEqual("%s files are unchanged" % total_files, rs.get_message().strip())

        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recipe_get_dir_exists(self):
        kitchen_name = 'CLI-Top'
        recipe_name = 'simple'
        temp_dir, kitchen_dir, recipe_dir = self._make_recipe_dir(recipe_name, kitchen_name, change_dir=True)
        rv = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name)
        msg = rv.get_message()
        self.assertTrue(recipe_name in msg)
        matches = re.match(r"([0-9]*) new or missing files", msg)
        self.assertTrue(int(matches.group(1)) >= 16)
        self.assertTrue('new or missing files' in msg)
        self.assertTrue(os.path.exists(os.path.join(kitchen_dir, recipe_name)))
        shutil.rmtree(temp_dir, ignore_errors=True)

    # get recipe inside an unchanged recipe
    def test_recipe_get_unchanged(self):
        kitchen_name = 'CLI-Top'
        recipe_name = 'simple'
        temp_dir, recipe_dir = self._get_recipe_to_disk(kitchen_name, recipe_name)
        rs = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name, start_dir=os.path.dirname(recipe_dir))
        self.assertTrue('Nothing to do', rs.get_message())
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertEqual('%s files are unchanged' % get_total_files(recipe_dir), rs.get_message().strip())

    def test_recipe_get_negative(self):
        kitchen_name = 'CLI-Top'
        recipe_name = 'simple_fogfogkfok'
        temp_dir, kitchen_dir = self._make_kitchen_dir(kitchen_name, change_dir=True)
        rc = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name)
        self.assertFalse(rc.ok())
        self.assertTrue('Unable to find recipe %s' % recipe_name in rc.get_message())
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_recipe_get_auto_merge(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'
        file_name = 'simple-file.txt'

        # check out the recipe to location 1: temp_dir_1
        temp_dir_1, recipe_dir_1 = self._get_recipe_to_disk(kitchen_name, recipe_name)
        file_path_1 = os.path.join(recipe_dir_1, file_name)
        file_content_before = DKFileHelper.read_file(file_path_1)

        # check out the recipe to a different location: temp_dir_2
        temp_dir_2, recipe_dir_2 = self._get_recipe_to_disk(kitchen_name, recipe_name)
        # add a new line to simple-file.txt in temp_dir_2
        file_path_2 = os.path.join(recipe_dir_2, file_name)
        new_line = "a new line at %s" % time.time()
        with open(file_path_2, 'a') as modify_file:
            modify_file.write('%s\n' % new_line)
            modify_file.flush()

        # update recipe to remote from temp_dir_2
        DKCloudCommandRunner.update_all_files(self._api, kitchen_name, recipe_name, recipe_dir_2, "add new line")

        # get recipe again from first location temp_dir_1,
        # it should auto merge simple-file.txt
        rc = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name, start_dir=recipe_dir_1)
        self.assertTrue(rc.ok())
        self.assertEqual("Auto-merging 'simple-file.txt'", rc.get_message().rstrip())

        # check simple-file.txt has the new line after auto merge
        file_content_after = DKFileHelper.read_file(file_path_1).rstrip().split("\n")
        lines_before = file_content_before.rstrip().split("\n")
        lines_before.append(new_line)
        self.assertListEqual(lines_before, file_content_after)

    def test_recipe_get_no_overwrite(self):
        kitchen_name = 'CLI-Top'
        recipe_name = 'simple'
        temp_dir, recipe_dir = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # Modify the local file.
        simple_file_path = os.path.join(recipe_dir, "simple-file.txt")
        simple_file_last_line = "last line: now is %s" % time.time()
        with open(simple_file_path, 'a') as modify_file:
            modify_file.write(simple_file_last_line)
            modify_file.flush()

        # Delete something local, so it's remote only.
        os.remove(os.path.join(recipe_dir, 'variations.json'))
        os.remove(os.path.join(recipe_dir, 'node1', 'data_sources', 'DKDataSource_NoOp.json'))

        # Create a new file, so there is a local only file.
        with open(os.path.join(recipe_dir, "new_local_file.txt"), 'w') as new_local_file:
            new_local_file.write('peccary\n')
            new_local_file.flush()

        # Create a new directory with file
        subdir = os.path.join(recipe_dir, 'subdir')
        os.mkdir(subdir)
        with open(os.path.join(subdir, "new_local_file_in_subdir.txt"), 'w') as new_local_file:
            new_local_file.write('peccary\n')
            new_local_file.flush()

        rc = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        expected_result = ('1 files are modified on local:\n'
                           '	simple-file.txt\n'
                           '\n'
                           '2 files are local only:\n'
                           '	new_local_file.txt\n'
                           '	subdir/new_local_file_in_subdir.txt\n'
                           '\n'
                           '1 directories are local only:\n'
                           '	subdir\n'
                           '\n'
                           '2 files are remote only:\n'
                           '	node1/data_sources/DKDataSource_NoOp.json\n'
                           '	variations.json')
        self.assertTrue(DKPathHelper.normalize(expected_result, DKPathHelper.WIN) in rc.get_message())

        # get recipe without overwrite
        rc = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name, start_dir=os.path.dirname(recipe_dir))
        self.assertTrue(rc.ok())
        expected_result = ('2 new or missing files from remote:\n'
                           '	node1/data_sources/DKDataSource_NoOp.json\n'
                           '	variations.json')
        self.assertEqual(DKPathHelper.normalize(expected_result, DKPathHelper.WIN), rc.get_message().strip())

        # check recipe status after recipe-get without overwrite
        rc = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        expected_result = ('1 files are modified on local:\n'
                           '\tsimple-file.txt\n'
                           '\n'
                           '2 files are local only:\n'
                           '\tnew_local_file.txt\n'
                           '\tsubdir/new_local_file_in_subdir.txt\n'
                           '\n'
                           '1 directories are local only:\n'
                           '\tsubdir\n')
        self.assertTrue(DKPathHelper.normalize(expected_result, DKPathHelper.WIN) in rc.get_message())

        # check deleted files are restored
        self.assertTrue(os.path.isfile(os.path.join(recipe_dir, 'variations.json')))
        self.assertTrue(os.path.isfile(os.path.join(recipe_dir, 'node1', 'data_sources', 'DKDataSource_NoOp.json')))

        # check local changes are not overwritten
        file_content = DKFileHelper.read_file(simple_file_path)
        self.assertEqual(simple_file_last_line, file_content.splitlines()[-1])
        self.assertEqual('peccary\n', DKFileHelper.read_file(os.path.join(recipe_dir, "new_local_file.txt")).replace('\r', ''))
        self.assertEqual('peccary\n', DKFileHelper.read_file(os.path.join(subdir, "new_local_file_in_subdir.txt")).replace('\r', ''))

        # check local new files are not added to FILE_SHA
        file_sha = self._get_file_sha(os.path.dirname(recipe_dir), recipe_name)
        self.assertFalse(os.path.join(recipe_name, 'new_local_file.txt') in file_sha)
        self.assertFalse(os.path.join(recipe_name, 'new_local_file_in_subdir.txt') in file_sha)

        # check local deleted files are not removed from FILE_SHA
        self.assertIsNotNone(file_sha.get(os.path.join(recipe_name, 'variations.json')))
        self.assertIsNotNone(file_sha.get(os.path.join(recipe_name, os.path.normpath('node1/data_sources/DKDataSource_NoOp.json'))))

    # get recipe with overwrite in a changed recipe
    def test_recipe_get_overwrite(self):
        kitchen_name = 'CLI-Top'
        recipe_name = 'simple'
        temp_dir, recipe_dir = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # add a new file in local
        local_new_file_path = os.path.join(recipe_dir, DKPathHelper.normalize('node1/local_new_file.json', DKPathHelper.WIN))
        with open(local_new_file_path, 'w') as f:
            f.write('This is my new file. Hooray!')
        # modify a file in local
        simple_file_path = os.path.join(recipe_dir, 'simple-file.txt')
        simple_file_content = DKFileHelper.read_file(simple_file_path)
        with open(simple_file_path, 'w') as f:
            f.write('a new line')
        # delete a file in local
        delete_file_path = os.path.join(recipe_dir, 'description.json')
        os.remove(delete_file_path)

        # recipe-status should list local changes
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        expected_result = ('1 files are modified on local:\n'
                           '	simple-file.txt\n'
                           '\n'
                           '1 files are local only:\n'
                           '	node1/local_new_file.json\n'
                           '\n'
                           '1 files are remote only:\n'
                           '	description.json\n')
        self.assertTrue(DKPathHelper.normalize(expected_result, DKPathHelper.WIN) in rs.get_message())

        # overwrite get recipe
        rs = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name,
                                             start_dir=os.path.dirname(recipe_dir),
                                             delete_local=True,
                                             overwrite=True,
                                             yes=True)
        self.assertTrue(rs.ok())
        expected_result = ('deleting local file: %s\n'
                           '\n'
                           '1 new or missing files from remote:\n'
                           '\tdescription.json\n'
                           'Getting from remote \'simple-file.txt\'') % local_new_file_path
        self.assertEqual(expected_result, rs.get_message().strip())

        # recipe-status should return "files are unchanged" now
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertEqual("%s files are unchanged" % get_total_files(recipe_dir), rs.get_message().strip())

        self.assertTrue(os.path.isfile(delete_file_path))  # deleted file should be restored
        self.assertFalse(os.path.isfile(local_new_file_path))  # local file should be deleted
        self.assertEqual(simple_file_content, DKFileHelper.read_file(simple_file_path))  # modified file should be reverted

        file_sha = self._get_file_sha(os.path.dirname(recipe_dir), recipe_name)
        # local files should not be added to FILE_SHA
        self.assertFalse(os.path.join(recipe_name, os.path.normpath('node1/local_new_file.json')) in file_sha)
        # locally deleted files should not be removed from FILE_SHA
        self.assertIsNotNone(file_sha.get(os.path.join(recipe_name, 'description.json')))
        # modified files should still be in FILE_SHA
        self.assertIsNotNone(file_sha.get(os.path.join(recipe_name, 'simple-file.txt')))

    def test_recipe_get_overwrite_no_delete(self):
        kitchen_name = 'CLI-Top'
        recipe_name = 'simple'
        temp_dir, recipe_dir = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # add a new file in local
        local_new_file_path = os.path.join(recipe_dir, os.path.normpath('node1/local_new_file.json'))
        with open(local_new_file_path, 'w') as f:
            f.write('This is my new file. Hooray!')
        # modify a file in local
        simple_file_path = os.path.join(recipe_dir, 'simple-file.txt')
        simple_file_content = DKFileHelper.read_file(simple_file_path)
        with open(simple_file_path, 'w') as f:
            f.write('a new line')
        # delete a file in local
        delete_file_path = os.path.join(recipe_dir, 'description.json')
        os.remove(delete_file_path)

        # recipe-status should list local changes
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        expected_result = ('1 files are modified on local:\n'
                           '	simple-file.txt\n'
                           '\n'
                           '1 files are local only:\n'
                           '	node1/local_new_file.json\n'
                           '\n'
                           '1 files are remote only:\n'
                           '	description.json\n')
        self.assertTrue(DKPathHelper.normalize(expected_result, DKPathHelper.WIN) in rs.get_message())

        # overwrite get recipe
        rs = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name,
                                             start_dir=os.path.dirname(recipe_dir),
                                             delete_local=False,
                                             overwrite=True,
                                             yes=True)
        self.assertTrue(rs.ok())
        self.assertTrue('deleting local file' not in rs.get_message().strip())

        # recipe-status should return "files are unchanged" now
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        expected_local_files = 1
        expected_unchanged_files = get_total_files(recipe_dir) - expected_local_files
        expected_message = '%d files are local only:\n\tnode1/local_new_file.json\n\n%d files are unchanged' % (expected_local_files, expected_unchanged_files)
        self.assertEqual(DKPathHelper.normalize(expected_message, DKPathHelper.WIN), rs.get_message().strip())

        self.assertTrue(os.path.isfile(delete_file_path))  # deleted file should be restored
        self.assertTrue(os.path.isfile(local_new_file_path))  # local file should not be deleted
        self.assertEqual(simple_file_content, DKFileHelper.read_file(simple_file_path))  # modified file should be reverted

        file_sha = self._get_file_sha(os.path.dirname(recipe_dir), recipe_name)
        # local files should not be added to FILE_SHA
        self.assertFalse(os.path.join(recipe_name, os.path.normpath('node1/local_new_file.json')) in file_sha)
        # modified files should still be in FILE_SHA
        self.assertIsNotNone(file_sha.get(os.path.join(recipe_name, 'simple-file.txt')))

    def test_recipe_get_overwrite_delete(self):
        kitchen_name = 'CLI-Top'
        recipe_name = 'simple'
        temp_dir, recipe_dir = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # add a new file in local
        local_new_file_path = os.path.join(recipe_dir, os.path.normpath('node1/local_new_file.json'))
        with open(local_new_file_path, 'w') as f:
            f.write('This is my new file. Hooray!')
        # modify a file in local
        simple_file_path = os.path.join(recipe_dir, 'simple-file.txt')
        simple_file_content = DKFileHelper.read_file(simple_file_path)
        with open(simple_file_path, 'w') as f:
            f.write('a new line')
        # delete a file in local
        delete_file_path = os.path.join(recipe_dir, 'description.json')
        os.remove(delete_file_path)

        # add a new file in local
        local_new_file_path = os.path.join(recipe_dir, 'my-root-folder')
        local_new_file_path_full = os.path.join(recipe_dir, os.path.normpath('my-root-folder/my-root-1.txt'))
        os.mkdir(local_new_file_path)
        with open(local_new_file_path_full, 'w') as f:
            f.write('This is my new file. Hooray!')

        local_new_file_path = os.path.join(recipe_dir, 'my-root.txt')
        with open(local_new_file_path, 'w') as f:
            f.write('This is my new file. Hooray!')

        local_new_file_path1 = os.path.join(recipe_dir, 'do-nothing-node')
        local_new_file_path2 = os.path.join(recipe_dir, os.path.normpath('do-nothing-node/my-folder/'))
        local_new_file_path_full = os.path.join(recipe_dir, os.path.normpath('do-nothing-node/my-folder/my-2.txt'))
        os.mkdir(local_new_file_path1)
        os.mkdir(local_new_file_path2)
        with open(local_new_file_path_full, 'w') as f:
            f.write('This is my new file. Hooray!')

        # add a new empty directory in local
        local_new_dir_1_path = os.path.join(recipe_dir, 'my-empty-folder-1')
        os.mkdir(local_new_dir_1_path)

        local_new_dir_2_path = os.path.join(recipe_dir, os.path.normpath('node1/my-empty-folder-2'))
        os.mkdir(local_new_dir_2_path)

        # recipe-status
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        expected_result = """1 files are modified on local:
	simple-file.txt

4 files are local only:
	do-nothing-node/my-folder/my-2.txt
	my-root-folder/my-root-1.txt
	my-root.txt
	node1/local_new_file.json

5 directories are local only:
	do-nothing-node
	do-nothing-node/my-folder
	my-empty-folder-1
	my-root-folder
	node1/my-empty-folder-2

1 files are remote only:
	description.json"""
        self.assertTrue(DKPathHelper.normalize(expected_result, DKPathHelper.WIN) in rs.get_message())

        # overwrite get recipe
        rs = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name,
                                             start_dir=os.path.dirname(recipe_dir),
                                             delete_local=True,
                                             overwrite=True,
                                             yes=True)
        self.assertTrue(rs.ok())

        self.assertTrue('deleting local file: %s' % os.path.join(recipe_dir, 'my-root.txt') in rs.get_message().strip())
        self.assertTrue('deleting local file: %s' % os.path.join(recipe_dir, os.path.normpath('do-nothing-node/my-folder/my-2.txt')) in rs.get_message().strip())
        self.assertTrue('deleting local file: %s' % os.path.join(recipe_dir, os.path.normpath('node1/local_new_file.json')) in rs.get_message().strip())
        self.assertTrue('deleting local file: %s' % os.path.join(recipe_dir, os.path.normpath('my-root-folder/my-root-1.txt')) in rs.get_message().strip())

        self.assertTrue('deleting local directory: %s' % os.path.join(recipe_dir, os.path.normpath('do-nothing-node/my-folder')) in rs.get_message().strip())
        self.assertTrue('deleting local directory: %s' % os.path.join(recipe_dir, os.path.normpath('node1/my-empty-folder-2')) in rs.get_message().strip())
        self.assertTrue('deleting local directory: %s' % os.path.join(recipe_dir, 'my-root-folder') in rs.get_message().strip())
        self.assertTrue('deleting local directory: %s' % os.path.join(recipe_dir, 'my-empty-folder-1') in rs.get_message().strip())
        self.assertTrue('deleting local directory: %s' % os.path.join(recipe_dir, 'do-nothing-node') in rs.get_message().strip())

        self.assertTrue("Getting from remote 'simple-file.txt'" in rs.get_message().strip())

        missing_file_message = "1 new or missing files from remote:\n	description.json"
        self.assertTrue(missing_file_message in rs.get_message().strip())

        # recipe-status should return everything unchanged
        rs = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertTrue(rs.ok())
        self.assertTrue('modified' not in rs.get_message().strip())
        self.assertTrue('local' not in rs.get_message().strip())
        self.assertTrue('remote' not in rs.get_message().strip())
        self.assertTrue('%d files are unchanged' % get_total_files(recipe_dir) in rs.get_message().strip())

    def test_recipe_get_remote_overwrite(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'
        _, recipe_dir_1 = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # add a file in remote
        recipe_dir_2, remote_new_file_path = self._add_new_file_in_remote(kitchen_name, recipe_name, "remote-new-file.txt")
        # modify a file in remote
        local_and_remote_modified_file_name = "remote_and_local_modify.txt"
        _, remote_modified_file_path = self._update_file_in_remote(kitchen_name, recipe_name, local_and_remote_modified_file_name,
                                                                   recipe_dir_2)
        remote_modified_file_content = DKFileHelper.read_file(remote_modified_file_path)
        # delete a file in remote
        remote_delete_file_name = "remote_delete_file.txt"
        remote_delete_file_path = os.path.join(recipe_dir_1, remote_delete_file_name)
        self._delete_file_in_remote(kitchen_name, recipe_name, remote_delete_file_name)

        # update file in local
        update_file_in_local(recipe_dir_1, local_and_remote_modified_file_name)

        rc = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir_1)
        self.assertTrue(rc.ok())

        expected_result = ('1 files are modified on both local and remote:\n'
                           '	remote_and_local_modify.txt\n'
                           '\n'
                           '1 files are local only:\n'
                           '	remote_delete_file.txt\n'
                           '\n'
                           '1 files are remote only:\n'
                           '	remote-new-file.txt')
        self.assertTrue(expected_result in rc.get_message())

        rc = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name,
                                             start_dir=os.path.dirname(recipe_dir_1),
                                             overwrite=True,
                                             delete_local=True,
                                             yes=True)
        expected_result = ('deleting local file: %s\n'
                           '\n'
                           '1 new or missing files from remote:\n'
                           '	remote-new-file.txt\n'
                           'Getting from remote \'remote_and_local_modify.txt\'') % remote_delete_file_path
        self.assertEqual(expected_result, rc.get_message().strip())

        # remote new file should be added to local
        self.assertTrue(os.path.isfile(remote_new_file_path))
        # remote deleted file should be deleted in local as well
        self.assertFalse(os.path.isfile(remote_delete_file_path))
        # local modified file should be overwritten with the latest change from remote
        self.assertEqual(remote_modified_file_content.strip(),
                         DKFileHelper.read_file(os.path.join(recipe_dir_1, local_and_remote_modified_file_name)).strip())

        rc = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir_1)
        self.assertEqual('%s files are unchanged\n' % get_total_files(recipe_dir_1), rc.get_message())

    def test_recipe_get_remote_no_overwrite_no_delete(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'
        _, recipe_dir_1 = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # add a file in remote
        recipe_dir_2, remote_new_file_path = self._add_new_file_in_remote(kitchen_name, recipe_name, "remote-new-file.txt")
        # modify a file in remote
        local_and_remote_modified_file_name = "remote_and_local_modify.txt"
        _, remote_modified_file_path = self._update_file_in_remote(kitchen_name, recipe_name, local_and_remote_modified_file_name,
                                                                   recipe_dir_2)
        remote_modified_file_content = DKFileHelper.read_file(remote_modified_file_path)
        # delete a file in remote
        remote_delete_file_name = "remote_delete_file.txt"
        remote_delete_file_path = os.path.join(recipe_dir_1, remote_delete_file_name)
        self._delete_file_in_remote(kitchen_name, recipe_name, remote_delete_file_name)

        # update file in local
        update_file_in_local(recipe_dir_1, local_and_remote_modified_file_name)

        rc = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir_1)
        self.assertTrue(rc.ok())
        expected_result = ('1 files are modified on both local and remote:\n'
                           '	remote_and_local_modify.txt\n'
                           '\n'
                           '1 files are local only:\n'
                           '	remote_delete_file.txt\n'
                           '\n'
                           '1 files are remote only:\n'
                           '	remote-new-file.txt')
        self.assertTrue(expected_result in rc.get_message())

        rc = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name, start_dir=os.path.dirname(recipe_dir_1))
        expected_result = ('1 new or missing files from remote:\n'
                           '	remote-new-file.txt\n'
                           'Auto-merging \'remote_and_local_modify.txt\'\n'
                           'CONFLICT (content): Merge conflict in remote_and_local_modify.txt')
        self.assertEqual(expected_result, rc.get_message().strip())

        # remote new file should be added to local
        self.assertTrue(os.path.isfile(remote_new_file_path))
        # remote deleted file should still exist in local
        self.assertTrue(os.path.isfile(remote_delete_file_path))
        # modified file should not equal to the latest change from remote
        self.assertNotEqual(remote_modified_file_content,
                            DKFileHelper.read_file(os.path.join(recipe_dir_1, local_and_remote_modified_file_name)))

        rc = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir_1)
        expected_result = ('1 files are modified on local:\n'
                           '	remote_and_local_modify.txt\n'
                           '\n'
                           '1 files are local only:\n'
                           '	remote_delete_file.txt')
        self.assertTrue(expected_result in rc.get_message())

    def test_recipe_status(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'

        temp_dir, recipe_dir_1 = self._get_recipe_to_disk(kitchen_name, recipe_name)
        rc = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir_1)
        rs = rc.get_message()
        self.assertNotRegexpMatches(rs, '^ERROR')
        matches = re.match(r"([0-9]*) files are unchanged", rs)
        self.assertTrue(int(matches.group(1)) >= 16)
        self.assertTrue('files are unchanged' in rs)

        # add a new file in remote
        recipe_dir_2, _ = self._add_new_file_in_remote(kitchen_name, recipe_name, "remote_new_file.txt")
        # change a file in remote
        self._update_file_in_remote(kitchen_name, recipe_name, "remote_modify_file.txt", recipe_dir_2)
        self._update_file_in_remote(kitchen_name, recipe_name, "remote_and_local_modify.txt", recipe_dir_2)
        # delete a file in remote
        self._delete_file_in_remote(kitchen_name, recipe_name, "remote_delete_file.txt")

        # Modify existing file
        with open(os.path.join(recipe_dir_1, 'local_modify_file.txt'), 'w') as f:
            f.write('BooGa BooGa')
        with open(os.path.join(recipe_dir_1, 'remote_and_local_modify.txt'), 'w') as f:
            f.write('BooGa BooGa')
        # Add a new file
        with open(os.path.join(recipe_dir_1, os.path.normpath('node1/local_new_file.json')), 'w') as f:
            f.write('This is my new file. Hooray!')
        # Delete a file
        os.remove(os.path.join(recipe_dir_1, os.path.normpath('node1/post_condition.json')))
        # Remove a directory
        shutil.rmtree(os.path.join(recipe_dir_1, os.path.normpath('node1/data_sinks')))

        rc = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir_1)
        rs = rc.get_message()

        self.assertNotRegexpMatches(rs, '^ERROR')
        match = re.search(r"([0-9]*) files are unchanged", rs)
        self.assertTrue(int(match.group(1)) >= 15)
        self.assertTrue('files are unchanged' in rs)

        expected_result = (u'1 files are modified on local:\n'
                           u'\tlocal_modify_file.txt\n'
                           u'\n'
                           #u'1 files are modified on remote:\n'
                           #u'\tremote_modify_file.txt\n'
                           #u'\n'
                           u'1 files are modified on both local and remote:\n'
                           u'\tremote_and_local_modify.txt\n'
                           u'\n'
                           u'2 files are local only:\n'
                           u'\tnode1/local_new_file.json\n'
                           u'\tremote_delete_file.txt\n'
                           u'\n'
                           u'4 files are remote only:\n'
                           u'\tnode1/data_sinks/DKDataSink_NoOp.json\n'
                           u'\tnode1/post_condition.json\n'
                           u'\tremote_modify_file.txt\n'
                           u'\tremote_new_file.txt\n'
                           u'\n'
                           u'1 directories are remote only:\n'
                           u'\tnode1/data_sinks\n')

        self.assertTrue(DKPathHelper.normalize(expected_result, DKPathHelper.WIN) in rs)

    def test_recipe_delete(self):
        existing_kitchen_name = 'master'
        recipe_name = 'parallel-recipe-test'
        kitchen_name = self._add_my_guid('test-kitchen-recipe-delete')

        # setup
        self._delete_and_clean_kitchen(kitchen_name)

        # create kitchen
        rs = DKCloudCommandRunner.create_kitchen(self._api, existing_kitchen_name, kitchen_name)
        self.assertTrue(rs.ok())

        temp_dir, kitchen_dir = self._make_kitchen_dir(kitchen_name, change_dir=True)
        DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name)
        new_path = os.path.join(kitchen_dir, recipe_name)

        # check previous status
        recipe_sha_dir = os.path.join(kitchen_dir, '.dk', 'recipes', recipe_name)
        recipe_dir = os.path.join(kitchen_dir, recipe_name)
        self.assertTrue(os.path.exists(recipe_dir))
        self.assertTrue(os.path.exists(recipe_sha_dir))

        # recipe delete
        rs = DKCloudCommandRunner.recipe_delete(self._api, kitchen_name, recipe_name)
        self.assertTrue(rs.ok())

        # check status after operation
        self.assertFalse(os.path.exists(recipe_dir))
        self.assertFalse(os.path.exists(recipe_sha_dir))

        # cleanup
        self._delete_and_clean_kitchen(kitchen_name)
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

        # Cleanup old state
        self._delete_and_clean_kitchen(test_kitchen)

        # Get the original file. Helper function handles the directories.
        original_file = self._get_recipe_file(parent_kitchen, recipe_name, recipe_file_key, file_name)

        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, test_kitchen)
        self.assertTrue(rs.ok())

        # Get the new kitchen to a temp folder
        temp_dir, test_kitchen_dir = self._make_kitchen_dir(test_kitchen, change_dir=True)
        new_kitchen_file = self._get_recipe_file(test_kitchen, recipe_name, recipe_file_key, file_name,
                                                 test_kitchen_dir)
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
        working_dir = os.path.join(test_kitchen_dir, recipe_name)
        os.chdir(working_dir)
        rc = DKCloudCommandRunner.update_file(self._api, test_kitchen, recipe_name, working_dir, message, api_file_key)
        self.assertTrue(rc.ok())
        new_kitchen_file3 = self._get_recipe_file(test_kitchen, recipe_name, recipe_file_key, file_name)
        new_kitchen_file2_formatted = DKJSONParser.format_file(new_kitchen_file2)
        self.assertEqual(new_kitchen_file2_formatted, new_kitchen_file3)

        # cleanup
        self._delete_and_clean_kitchen(test_kitchen)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_update_file_with_unicode(self):
        # setup
        parent_kitchen = 'CLI-Top'
        test_kitchen = self._add_my_guid('CLI-test_update_file_unicode')
        recipe_name = 'simple'
        recipe_file_key = recipe_name
        file_name = 'simple-file.txt'
        message = 'test simple-file.txt with unicode'
        api_file_key = file_name
        update_str = 'some unicode 测试'

        # Cleanup old state
        self._delete_and_clean_kitchen(test_kitchen)

        # Get the original file. Helper function handles the directories.
        original_file = self._get_recipe_file(parent_kitchen, recipe_name, recipe_file_key, file_name)

        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, test_kitchen)
        self.assertTrue(rs.ok())

        # Get the new kitchen to a temp folder
        temp_dir, test_kitchen_dir = self._make_kitchen_dir(test_kitchen, change_dir=True)
        new_kitchen_file = self._get_recipe_file(test_kitchen, recipe_name, recipe_file_key, file_name,
                                                 test_kitchen_dir)
        self.assertEqual(original_file, new_kitchen_file)

        new_kitchen_file_abspath = os.path.join(test_kitchen_dir, os.path.join(recipe_file_key, file_name))
        with open(new_kitchen_file_abspath, 'w') as rfile:
            rfile.seek(0)
            rfile.truncate()
            rfile.write(update_str)

        # test
        working_dir = os.path.join(test_kitchen_dir, recipe_name)
        os.chdir(working_dir)
        rc = DKCloudCommandRunner.update_file(self._api, test_kitchen, recipe_name, working_dir, message, api_file_key)
        self.assertTrue(rc.ok())

        new_kitchen_file = self._get_recipe_file(test_kitchen, recipe_name, recipe_file_key, file_name)
        self.assertEqual(update_str, new_kitchen_file)

        # cleanup
        self._delete_and_clean_kitchen(test_kitchen)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_util_funcs(self):

        paths_to_check = ['description.json', 'graph.json', 'simple-file.txt', 'node2_hide', 'node2_hide/my_file.txt', 'node1hide/subdir/hide-me.txt''variables.json', 'variations.json', 'node2/data_sinks', 'node1/data_sinks', 'node2', 'node1', 'node1/data_sources', 'resources', 'node2/data_sources']
        minimal_paths = DKCloudCommandRunner.find_minimal_paths_to_get(paths_to_check)
        self.assertIsNotNone(minimal_paths)

    def test_update_all_not_delete_remote(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'

        _, recipe_dir = self._get_recipe_to_disk(kitchen_name, recipe_name)
        delete_file_name = 'simple-file.txt'
        delete_file_path = os.path.join(recipe_dir, delete_file_name)
        os.remove(delete_file_path)

        rc = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertTrue(rc.ok())
        expected_result = ('1 files are remote only:\n'
                           '\tsimple-file.txt\n'
                           '\n'
                           '%s files are unchanged\n') % get_total_files(recipe_dir)
        self.assertEqual(expected_result, rc.get_message())

        rc = DKCloudCommandRunner.update_all_files(self._api, kitchen_name, recipe_name, recipe_dir, 'update all', delete_remote=False)
        self.assertTrue(rc.ok())
        expected_result = ('Update results:\n'
                           '\n'
                           'New files:\n'
                           '	None\n'
                           'Updated files:\n'
                           '	None\n'
                           'Deleted files:\n'
                           '	None\n'
                           '\n'
                           'Issues:\n'
                           '\n'
                           'No issues found')
        self.assertEqual(expected_result, rc.get_message())
        self.assertFalse(os.path.isfile(delete_file_path))

        # local deleted file should still be in FILE_SHA
        file_sha = self._get_file_sha(os.path.dirname(recipe_dir), recipe_name)
        self.assertIsNotNone(file_sha.get(os.path.join(recipe_name, delete_file_name)))

        rc = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name, start_dir=os.path.dirname(recipe_dir))
        self.assertTrue(rc.ok())
        # local deleted file should be restored from remote
        self.assertTrue(os.path.isfile(delete_file_path))

    def test_update_all_delete_remote(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'
        _, recipe_dir = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # make local changes
        new_file_name = 'local_new_file.txt'
        new_file_path = add_new_file_in_local(recipe_dir, new_file_name)
        new_file_content = DKFileHelper.read_file(new_file_path)

        update_file_name = 'local_modify_file.txt'
        update_file_path = update_file_in_local(recipe_dir, update_file_name)
        update_file_content = DKFileHelper.read_file(update_file_path)

        delete_file_name = 'simple-file.txt'
        delete_file_path = delete_file_in_local(recipe_dir, delete_file_name)
        self.assertFalse(os.path.exists(delete_file_path))

        file_sha = self._get_file_sha(os.path.dirname(recipe_dir), recipe_name)
        update_file_sha_name = os.path.join(recipe_name, update_file_name)
        updated_file_old_sha = file_sha.get(update_file_sha_name)
        self.assertIsNotNone(updated_file_old_sha)

        rc = DKCloudCommandRunner.update_all_files(self._api, kitchen_name, recipe_name, recipe_dir, 'update all', delete_remote=True)
        expected_result = ('Update results:\n'
                           '\n'
                           'New files:\n'
                           '	local_new_file.txt\n'
                           'Updated files:\n'
                           '	local_modify_file.txt\n'
                           'Deleted files:\n'
                           '	simple-file.txt\n'
                           '\n'
                           'Issues:\n'
                           '\n'
                           'No issues found')
        self.assertEqual(expected_result, rc.get_message())

        # new file should be added to FILE_SHA
        file_sha = self._get_file_sha(os.path.dirname(recipe_dir), recipe_name)
        self.assertTrue(os.path.join(recipe_name, new_file_name) in file_sha)
        # deleted file should be removed from FILE_SHA
        self.assertFalse(os.path.join(recipe_name, delete_file_name) in file_sha)
        # updated file's sha should be updated
        update_file_new_sha = file_sha.get(update_file_sha_name)
        self.assertIsNotNone(update_file_new_sha)
        self.assertNotEqual(update_file_new_sha, updated_file_old_sha)

        rc = DKCloudCommandRunner.recipe_status(self._api, kitchen_name, recipe_name, recipe_path_param=recipe_dir)
        self.assertTrue(rc.ok())
        self.assertEqual('%s files are unchanged\n' % get_total_files(recipe_dir), rc.get_message())

        # get recipe in a different location
        _, recipe_dir_2 = self._get_recipe_to_disk(kitchen_name, recipe_name)
        # check new file is added
        self.assertEqual(new_file_content, DKFileHelper.read_file(os.path.join(recipe_dir_2, new_file_name)))
        # check modified file is pushed to remote
        self.assertEqual(update_file_content, DKFileHelper.read_file(os.path.join(recipe_dir_2, update_file_name)))
        # check deleted file is not in remote
        self.assertFalse(os.path.exists(os.path.join(recipe_dir_2, delete_file_name)))

        # check FILE_SHA in the new recipe location
        file_sha = self._get_file_sha(os.path.dirname(recipe_dir_2), recipe_name)
        self.assertIsNotNone(file_sha.get(os.path.join(recipe_name, new_file_name)))
        self.assertFalse(os.path.join(recipe_name, delete_file_name) in file_sha)
        self.assertEqual(update_file_new_sha, file_sha.get(update_file_sha_name))

    def test_update_all_on_outdated_local(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'

        _, recipe_dir = self._get_recipe_to_disk(kitchen_name, recipe_name)
        # modify file in local
        remote_and_local_modify_file_name = 'remote_and_local_modify.txt'
        update_file_in_local(recipe_dir, remote_and_local_modify_file_name)
        # modify file in remote
        self._update_file_in_remote(kitchen_name, recipe_name, remote_and_local_modify_file_name)

        # recipe-update should return error
        rc = DKCloudCommandRunner.update_all_files(self._api, kitchen_name, recipe_name, recipe_dir, 'update all', delete_remote=True)
        self.assertTrue(rc.ok())
        expected_result = ('ERROR: 1 files have remote changes. Please run \'dk recipe-get\' first.\n'
                           '	remote_and_local_modify.txt')
        self.assertEqual(expected_result, rc.get_message())

    def test_update_all(self):
        parent_kitchen = 'CLI-Top'
        test_kitchen = self._add_my_guid('update_all')
        recipe_name = 'simple2'
        new = 'new.txt'
        deleted = 'deleted.txt'
        modified = 'modified.txt'
        subdir = 'subdir'
        subsubdir = os.path.join(subdir, 'subsubdir')
        subusubsubdir = os.path.join(subsubdir, 'subusubsubdir')

        emptysubdir = 'emptysubdir'

        self._delete_and_clean_kitchen(test_kitchen)
        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, test_kitchen)
        self.assertTrue(rs.ok())

        # make and cd to kitchen dir and get the recipe to disk
        temp_dir, kitchen_dir, recipe_dir = self._make_recipe_dir(recipe_name, test_kitchen)
        os.chdir(kitchen_dir)
        print 'Working in directory %s' % recipe_dir
        start_time = time.time()
        rs = DKCloudCommandRunner.get_recipe(self._api, test_kitchen, recipe_name)
        elapsed_recipe_status = time.time() - start_time
        print 'get_recipe - elapsed: %d' % elapsed_recipe_status
        self.assertTrue(rs.ok())

        os.chdir(recipe_dir)
        start_time = time.time()
        rc = DKCloudCommandRunner.recipe_status(self._api, test_kitchen, recipe_name)
        elapsed_recipe_status = time.time() - start_time
        print 'recipe_status - elapsed: %d' % elapsed_recipe_status
        msg = rc.get_message()
        self.assertTrue('files differ' not in msg)
        self.assertTrue('only on local' not in msg)
        self.assertTrue('only on remote' not in msg)

        # New, not added, file
        with open(new, 'w') as f:
            f.write('This is file %s\n' % new)

        with open(os.path.join('placeholder-node3', new), 'w') as f:
            f.write('This is file %s in placeholder-node3\n' % new)

        # Deleted File
        with open(deleted, 'w') as f:
            f.write('This is file %s\n' % deleted)
        rc = DKCloudCommandRunner.add_file(self._api, test_kitchen, recipe_name, 'Adding %s' % deleted, deleted)
        self.assertTrue(rc.ok())
        os.remove(deleted)

        # Modified File
        with open(modified, 'w') as f:
            f.write('This is file %s\n' % modified)
        rc = DKCloudCommandRunner.add_file(self._api, test_kitchen, recipe_name, 'Adding %s' % modified, modified)
        self.assertTrue(rc.ok())

        with open(modified, 'a') as f:
            f.write('This is a new line %s\n' % modified)

        # New empty subdirectory
        os.mkdir(emptysubdir)

        # New file in a subdirectory
        os.mkdir(subdir)
        os.mkdir(subsubdir)
        os.mkdir(subusubsubdir)

        with open(os.path.join(subsubdir, new), 'w') as f:
            f.write('This is file %s in subdirectory %s\n' % (new, subsubdir))

        with open(os.path.join(subsubdir, 'also_%s' % new), 'w') as f:
            f.write('This is file %s in subdirectory %s\n' % ('also_%s' % new, subsubdir))

        with open(os.path.join(subusubsubdir, 'again_%s' % new), 'w') as f:
            f.write('This is file %s in subdirectory %s\n' % ('also_%s' % new, subusubsubdir))

        # Delete a whole directory, and some files under there.
        shutil.rmtree('placeholder-node3', ignore_errors=True)

        # Make sure repo is in state we expect.
        start_time = time.time()
        rc = DKCloudCommandRunner.recipe_status(self._api, test_kitchen, recipe_name)
        elapsed_recipe_status = time.time() - start_time
        print 'recipe_status - elapsed: %d' % elapsed_recipe_status
        msg = rc.get_message()

        match = re.search(r"([0-9]*) files are unchanged", msg)
        self.assertTrue(int(match.group(1)) >= 10)
        self.assertTrue('files are unchanged' in msg)

        match = re.search(r"([0-9]*) files are modified", msg)
        self.assertTrue(int(match.group(1)) >= 1)
        self.assertTrue('files are modified' in msg)

        match = re.search(r"([0-9]*) files are local only", msg)
        self.assertTrue(int(match.group(1)) >= 1)
        self.assertTrue('files are local only' in msg)

        match = re.search(r"([0-9]*) files are remote only", msg)
        self.assertTrue(int(match.group(1)) >= 1)
        self.assertTrue('files are remote only' in msg)

        self.assertTrue(os.path.normpath('subdir/subsubdir/subusubsubdir') in msg)

        rc = DKCloudCommandRunner.update_all_files(self._api, test_kitchen, recipe_name, recipe_dir, 'update all', delete_remote=True)

        self.assertTrue(rc.ok())
        msg = rc.get_message()

        self.assertFalse(os.path.exists(emptysubdir), 'Directory %s has not been removed' % emptysubdir)

        self.assertTrue('Update results:' in msg)

        new_files_index = msg.find('New files:')
        updated_files_index = msg.find('Updated files:')
        deleted_files_index = msg.find('Deleted files:')
        issues_index = msg.find('Issues:')

        new_files_section = msg[new_files_index:updated_files_index]
        updated_files_section = msg[updated_files_index:deleted_files_index]
        deleted_files_section = msg[deleted_files_index:issues_index]
        issues_section = msg[issues_index:]

        self.assertTrue('new.txt' in new_files_section)
        self.assertTrue(os.path.normpath('subdir/subsubdir/also_new.txt') in new_files_section)
        self.assertTrue(os.path.normpath('subdir/subsubdir/new.txt') in new_files_section)
        self.assertTrue(os.path.normpath('subdir/subsubdir/subusubsubdir/again_new.txt') in new_files_section)

        self.assertTrue('modified.txt' in updated_files_section)

        self.assertTrue('deleted.txt' in deleted_files_section)
        self.assertTrue(os.path.normpath('placeholder-node3/description.json') in deleted_files_section)

        self.assertTrue('No issues found' in issues_section)

        self._delete_and_clean_kitchen(test_kitchen)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_add_file(self):
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

        # test negative
        rc = DKCloudCommandRunner.add_file(self._api, test_kitchen, recipe_name, message, 'badfile.txt')
        self.assertFalse(rc.ok())

        # create test kitchen
        self._delete_and_clean_kitchen(test_kitchen)
        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, test_kitchen)
        self.assertTrue(rs.ok())

        # make and cd to kitchen dir and get the recipe to disk
        temp_dir, kitchen_dir = self._make_kitchen_dir(test_kitchen, change_dir=True)
        os.chdir(kitchen_dir)
        self._get_recipe(test_kitchen, recipe_name)

        # create new file on disk
        try:
            os.chdir(recipe_name)
            with open(api_file_key, 'w') as f:
                f.write(file_contents)
        except ValueError, e:
            print('could not write file %s.' % e)
            self.assertTrue(False)

        # add file from disk THE TEST
        rc = DKCloudCommandRunner.add_file(self._api, test_kitchen, recipe_name, message, api_file_key)
        self.assertTrue(rc.ok())

        # make sure file is in kitchen (get file)
        file_contents2 = self._get_recipe_file(test_kitchen, recipe_name, recipe_file_key, file_name)
        self.assertEqual(file_contents, file_contents2, 'Create check')

        # cleanup
        self._delete_and_clean_kitchen(test_kitchen)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_file(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'
        file_name = 'local_modify_file.txt'

        # make local changes
        _, recipe_dir_1 = self._get_recipe_to_disk(kitchen_name, recipe_name)
        update_file_in_local(recipe_dir_1, file_name)

        # make remote changes
        _, file_path = self._update_file_in_remote(kitchen_name, recipe_name, file_name)
        remote_file_content = DKFileHelper.read_file(file_path)

        os.chdir(recipe_dir_1)
        rc = DKCloudCommandRunner.get_file(self._api, kitchen_name, recipe_name, file_name)
        self.assertTrue(rc.ok())

        # check file content is updated
        self.assertEqual(
            remote_file_content.replace('\r', ''),
            DKFileHelper.read_file(os.path.join(recipe_dir_1, file_name)).replace('\r', ''))
        # check file sha is updated
        file_sha = self._get_file_sha(os.path.dirname(recipe_dir_1), recipe_name)
        new_sha = file_sha.get(os.path.join(recipe_name, file_name))
        self.assertEqual(githash_by_file_name(os.path.join(recipe_dir_1, file_name)), new_sha)

    def test_delete_file(self):
        # setup
        parent_kitchen = 'CLI-Top'
        test_kitchen = 'Runner-test_delete_file'
        test_kitchen = self._add_my_guid(test_kitchen)
        recipe_name = 'simple'
        recipe_file_key = recipe_name
        file_name = 'description.json'
        message = 'test Delete Runner-test_delete_file'
        self._delete_and_clean_kitchen(test_kitchen)
        temp_dir, kitchen_dir = self._make_kitchen_dir(test_kitchen, change_dir=True)

        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, test_kitchen)
        self.assertTrue(rs.ok())
        os.chdir(kitchen_dir)

        self.assertTrue(self._get_recipe_file(test_kitchen, recipe_name, recipe_file_key, file_name) is not None)
        rv = DKCloudCommandRunner.get_recipe(self._api, test_kitchen, recipe_name)
        self.assertTrue(recipe_name in rv.get_message())
        target_file = os.path.join(kitchen_dir, os.path.join(recipe_file_key, file_name))
        self.assertTrue(os.path.isfile(target_file))  # the file is there
        os.remove(target_file)
        rs = DKCloudCommandRunner.delete_file(self._api, test_kitchen, recipe_name,
                                              message, file_name)
        self.assertTrue(rs.ok())
        self.assertTrue(self._get_recipe_file(test_kitchen, recipe_name, recipe_file_key, file_name) is None,
                        "Gone check")

        # cleanup
        self._delete_and_clean_kitchen(test_kitchen)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_order(self):
        kitchen = 'CLI-Top'
        recipe = 'simple'
        variation = 'simple-variation-now'
        rv = DKCloudCommandRunner.create_order(self._api, kitchen, recipe, variation)
        response = rv.get_payload()
        self.assertEquals('success', response['status'])
        self.assertTrue('Order ID is:' in rv.get_message())

    def test_delete_all_order(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_deleteall_orderRUN'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'simple'
        variation = 'simple-variation-now'
        DKCloudCommandRunner.delete_kitchen(self._api, new_kitchen)  # clean up junk
        rc = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, new_kitchen)
        self.assertTrue(rc.ok())
        rv = DKCloudCommandRunner.create_order(self._api, new_kitchen, recipe, variation)
        self.assertIsNotNone(rv)
        order_id = rv.get_payload()
        self.assertIsNotNone(variation in order_id)
        # test
        rc = DKCloudCommandRunner.delete_all_order(self._api, new_kitchen)
        self.assertTrue(rc.ok())
        # cleanup
        DKCloudCommandRunner.delete_kitchen(self._api, new_kitchen)

    def test_delete_one_order(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_deleteall_order-RUN'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'simple'
        variation = 'simple-variation-now'
        DKCloudCommandRunner.delete_kitchen(self._api, new_kitchen)  # clean up junk
        rc = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, new_kitchen)
        self.assertTrue(rc.ok())
        rv = DKCloudCommandRunner.create_order(self._api, new_kitchen, recipe, variation)
        self.assertIsNotNone(rv)
        order_id = rv.get_payload()['serving_hid']
        self.assertIsNotNone(variation in order_id)
        # test
        rc = DKCloudCommandRunner.delete_one_order(self._api, new_kitchen, order_id)
        self.assertTrue(rc.ok())
        # cleanup
        DKCloudCommandRunner.delete_kitchen(self._api, new_kitchen)

    def test_stop_order(self):
        # setup
        parent_kitchen = 'CLI-Top'
        new_kitchen = 'test_stop_order-RUN'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe = 'simple'
        variation = 'simple-variation-now'
        DKCloudCommandRunner.delete_kitchen(self._api, new_kitchen)  # clean up junk
        rc = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, new_kitchen)
        self.assertTrue(rc.ok())
        rv = DKCloudCommandRunner.create_order(self._api, new_kitchen, recipe, variation)
        self.assertIsNotNone(rv)
        order_id = rv.get_payload()['serving_hid']
        serving_chronos_id = rv.get_payload()['serving_chronos_id']
        self.assertTrue(variation in serving_chronos_id)
        # test
        rc = DKCloudCommandRunner.stop_order(self._api, new_kitchen, order_id)
        # todo: need to find a way for this to succeed
        self.assertTrue(rc.ok())
        # cleanup
        DKCloudCommandRunner.delete_kitchen(self._api, new_kitchen)

    def test_get_compiled_serving_from_recipe(self):
        # setup
        parent_kitchen = 'master'
        new_kitchen = 'test_get_compiled_serving_from_recipe=API'
        new_kitchen = self._add_my_guid(new_kitchen)
        recipe_name = 'parallel-recipe-test'
        variation_name = 'variation-test'
        self._delete_and_clean_kitchen(new_kitchen)

        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, new_kitchen)
        self.assertTrue(rs.ok())
        # test
        resp = DKCloudCommandRunner.get_compiled_serving(self._api, parent_kitchen, recipe_name, variation_name)
        self.assertTrue(resp.ok())
        # cleanup
        self._delete_and_clean_kitchen(new_kitchen)

    # test when the remote source kitchen has new modifications on resolved files, after kitchen-merge-preview
    def test_merge_kitchens_source_remote_modified_resolved(self):
        master_kitchen = 'CLI-Top'
        recipe_name = 'simple'
        file_name = 'simple-file.txt'
        from_kitchen, to_kitchen = self._setup_kitchens_for_merge(master_kitchen, recipe_name, file_name)

        # modify resolved file in remote from_kitchen
        _, file_path = self._update_file_in_remote(from_kitchen, recipe_name, file_name)
        # modify another file in remote from_kitchen
        self._update_file_in_remote(from_kitchen, recipe_name, "remote_modify_file.txt")

        # run kitchen-merge
        rc = DKCloudCommandRunner.kitchen_merge(self._api, from_kitchen, to_kitchen)

        # kitchen merge should fail
        self.assertFalse(rc.ok())
        expected_result = ('DKCloudCommandRunner Error.\n'
                           'Kitchen %s has new changes since last kitchen-merge-preview. Please run kitchen-merge-preview again.\n') % from_kitchen
        self.assertEqual(expected_result, rc.get_message())

    # test when the remote target kitchen has new modifications on resolved files, after kitchen-merge-preview
    def test_merge_kitchens_target_remote_modified_resolved(self):
        master_kitchen = 'CLI-Top'
        recipe_name = 'simple'
        file_name = 'simple-file.txt'
        from_kitchen, to_kitchen = self._setup_kitchens_for_merge(master_kitchen, recipe_name, file_name)

        # modify resolved file in remote to_kitchen
        _, file_path = self._update_file_in_remote(to_kitchen, recipe_name, file_name)
        latest_content = DKFileHelper.read_file(file_path)

        # modify another file in remote to_kitchen
        self._update_file_in_remote(to_kitchen, recipe_name, "remote_modify_file.txt")

        # run kitchen-merge
        rc = DKCloudCommandRunner.kitchen_merge(self._api, from_kitchen, to_kitchen)

        # kitchen merge should fail
        self.assertFalse(rc.ok())
        expected_result = ('DKCloudCommandRunner Error.\n'
                           'Kitchen %s has new changes since last kitchen-merge-preview. Please run kitchen-merge-preview again.\n') % to_kitchen
        self.assertEqual(expected_result, rc.get_message())

        # remote change should NOT be overridden
        _, recipe_dir = self._get_recipe_to_disk(to_kitchen, recipe_name)
        self.assertEqual(latest_content.replace('\r', ''), DKFileHelper.read_file(os.path.join(recipe_dir, file_name)).replace('\r', ''))

    def test_manual_merge_kitchens_edge_case_001(self):
        # 1 deleted file on source
        # 1 modification ons source and target -> conflict
        parent_kitchen = 'CLI-Top'
        recipe_name = 'simple'
        file_name = 'simple-file.txt'
        file_name_to_delete = 'remote_delete_file.txt'

        source_kitchen = 'cli_test_manual_merge_edge_case_001_source'
        target_kitchen = 'cli_test_manual_merge_edge_case_001_target'

        startup = True
        cleanup = True

        # Previous test cleanup
        if startup:
            self._delete_and_clean_kitchen(source_kitchen)
            self._delete_and_clean_kitchen(target_kitchen)

        # Create Kitchens
        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, source_kitchen)
        self.assertTrue(rs.ok())

        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, target_kitchen)
        self.assertTrue(rs.ok())

        # modify file in remote target kitchen
        contents = 'Target contents'
        _, file_path_target = self._update_file_in_remote(target_kitchen, recipe_name, file_name, file_content=contents)
        latest_content_target = DKFileHelper.read_file(file_path_target)

        # modify file in remote source kitchen
        contents = 'Source contents'
        _, file_path_source = self._update_file_in_remote(source_kitchen, recipe_name, file_name, file_content=contents)
        latest_content_source = DKFileHelper.read_file(file_path_source)

        # delete file in remote source kitchen
        DKCloudCommandRunner.delete_file(self._api, source_kitchen, recipe_name, "delete file %s" % file_name_to_delete, file_name_to_delete)

        # kitchen merge preview
        DKCloudCommandRunner.kitchen_merge_preview(self._api, source_kitchen, target_kitchen, True)

        # resolve conflicts
        file_path = os.path.join(recipe_name, file_name)
        home = expanduser('~')
        merge_dir = os.path.join(home, '.dk','test', 'merges')
        working_dir = os.path.join(merge_dir, '%s_to_%s' % (source_kitchen, target_kitchen))
        full_path = os.path.join(working_dir, file_path + '.base')
        resolved_contents = '{\t\t\t"Resolved": \t\t\t"contents"}'
        resolved_formatted_contents = '{\n    "Resolved": "contents"\n}\n'
        DKFileHelper.write_file(full_path, resolved_contents)
        DKCloudCommandRunner.file_resolve(self._api, source_kitchen, target_kitchen, file_path)

        # kitchen merge
        rc = DKCloudCommandRunner.kitchen_merge(self._api, source_kitchen, target_kitchen)
        self.assertTrue(rc.ok())

        # check the kitchen states are as desired
        _, recipe_path = self._get_recipe_to_disk(target_kitchen, recipe_name)
        self.assertFalse(os.path.isfile(os.path.join(recipe_path, file_name_to_delete)))
        self.assertTrue(os.path.isfile(os.path.join(recipe_path, file_name)))
        after_merge_content_target = DKFileHelper.read_file(os.path.join(recipe_path, file_name))
        self.assertFalse('\t' in after_merge_content_target)
        self.assertEqual(resolved_formatted_contents, after_merge_content_target)

        # cleanup
        if cleanup:
            self._delete_and_clean_kitchen(source_kitchen)
            self._delete_and_clean_kitchen(target_kitchen)

    def test_manual_merge_kitchens_edge_case_002(self):
        # 1 deleted file on source, and modified on target -> conflict
        parent_kitchen = 'CLI-Top'
        recipe_name = 'simple'
        file_name = 'simple-file.txt'

        source_kitchen = 'cli_test_manual_merge_edge_case_002_source'
        target_kitchen = 'cli_test_manual_merge_edge_case_002_target'

        startup = True
        cleanup = True

        # Previous test cleanup
        if startup:
            self._delete_and_clean_kitchen(source_kitchen)
            self._delete_and_clean_kitchen(target_kitchen)

        # Create Kitchens
        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, source_kitchen)
        self.assertTrue(rs.ok())

        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, target_kitchen)
        self.assertTrue(rs.ok())

        # modify file in remote target kitchen
        contents = 'Target contents'
        _, file_path_target = self._update_file_in_remote(target_kitchen, recipe_name, file_name, file_content=contents)
        latest_content_target = DKFileHelper.read_file(file_path_target)

        # delete file in remote source kitchen
        DKCloudCommandRunner.delete_file(self._api, source_kitchen, recipe_name,
                                         "delete file %s" % file_name, file_name)

        # kitchen merge preview
        DKCloudCommandRunner.kitchen_merge_preview(self._api, source_kitchen, target_kitchen, True)

        # resolve conflicts
        file_path = os.path.join(recipe_name, file_name)
        home = expanduser('~')
        merge_dir = os.path.join(home, '.dk', 'test', 'merges')
        working_dir = os.path.join(merge_dir, '%s_to_%s' % (source_kitchen, target_kitchen))
        full_path = os.path.join(working_dir, file_path + '.base')
        resolved_contents = 'Resolved contents'
        DKFileHelper.write_file(full_path, resolved_contents)
        DKCloudCommandRunner.file_resolve(self._api, source_kitchen, target_kitchen, file_path)

        # kitchen merge
        rc = DKCloudCommandRunner.kitchen_merge(self._api, source_kitchen, target_kitchen)
        self.assertTrue(rc.ok())

        # check the kitchen states are as desired
        _, recipe_path = self._get_recipe_to_disk(target_kitchen, recipe_name)
        self.assertTrue(os.path.isfile(os.path.join(recipe_path, file_name)))
        after_merge_content_target = DKFileHelper.read_file(os.path.join(recipe_path, file_name))
        self.assertEqual(resolved_contents, after_merge_content_target)

        # cleanup
        if cleanup:
            self._delete_and_clean_kitchen(source_kitchen)
            self._delete_and_clean_kitchen(target_kitchen)

    def test_manual_merge_kitchens_edge_case_003(self):
        # 1 deleted file on target, and modified on source -> conflict
        parent_kitchen = 'CLI-Top'
        recipe_name = 'simple'
        file_name = 'simple-file.txt'

        source_kitchen = 'cli_test_manual_merge_edge_case_003_source'
        target_kitchen = 'cli_test_manual_merge_edge_case_003_target'

        startup = True
        cleanup = True

        # Previous test cleanup
        if startup:
            self._delete_and_clean_kitchen(source_kitchen)
            self._delete_and_clean_kitchen(target_kitchen)

        # Create Kitchens
        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, source_kitchen)
        self.assertTrue(rs.ok())

        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, target_kitchen)
        self.assertTrue(rs.ok())

        # modify file in remote source kitchen
        contents = 'Source contents'
        _, file_path_source = self._update_file_in_remote(source_kitchen, recipe_name, file_name, file_content=contents)
        latest_content_source = DKFileHelper.read_file(file_path_source)

        # delete file in remote target kitchen
        DKCloudCommandRunner.delete_file(self._api, target_kitchen, recipe_name,
                                         "delete file %s" % file_name, file_name)

        # kitchen merge preview
        DKCloudCommandRunner.kitchen_merge_preview(self._api, source_kitchen, target_kitchen, True)

        # resolve conflicts
        file_path = os.path.join(recipe_name, file_name)
        home = expanduser('~')
        merge_dir = os.path.join(home, '.dk', 'test', 'merges')
        working_dir = os.path.join(merge_dir, '%s_to_%s' % (source_kitchen, target_kitchen))
        full_path = os.path.join(working_dir, file_path + '.base')
        resolved_contents = 'Resolved contents'
        DKFileHelper.write_file(full_path, resolved_contents)
        DKCloudCommandRunner.file_resolve(self._api, source_kitchen, target_kitchen, file_path)

        # kitchen merge
        rc = DKCloudCommandRunner.kitchen_merge(self._api, source_kitchen, target_kitchen)
        self.assertTrue(rc.ok())

        # check the kitchen states are as desired
        _, recipe_path = self._get_recipe_to_disk(target_kitchen, recipe_name)
        self.assertTrue(os.path.isfile(os.path.join(recipe_path, file_name)))
        after_merge_content_target = DKFileHelper.read_file(os.path.join(recipe_path, file_name))
        self.assertEqual(resolved_contents, after_merge_content_target)

        # cleanup
        if cleanup:
            self._delete_and_clean_kitchen(source_kitchen)
            self._delete_and_clean_kitchen(target_kitchen)

    def test_manual_merge_kitchens_edge_case_004(self):
        # file rename case:
        #   source: change simple-file.txt to simple-file-new.txt and move into resources
        #   target: change simple-file.txt contents
        parent_kitchen = 'CLI-Top'
        recipe_name = 'simple'
        file_name = 'simple-file.txt'

        source_kitchen = 'cli_test_manual_merge_edge_case_004_source'
        target_kitchen = 'cli_test_manual_merge_edge_case_004_target'

        startup = True
        cleanup = True

        # Previous test cleanup
        if startup:
            self._delete_and_clean_kitchen(source_kitchen)
            self._delete_and_clean_kitchen(target_kitchen)

        # Create Kitchens
        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, source_kitchen)
        self.assertTrue(rs.ok())

        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, target_kitchen)
        self.assertTrue(rs.ok())

        # modify file in remote target kitchen
        contents = 'Target contents'
        _, file_path_target = self._update_file_in_remote(target_kitchen, recipe_name, file_name, file_content=contents)
        latest_content_target = DKFileHelper.read_file(file_path_target)

        # delete file in remote source kitchen
        DKCloudCommandRunner.delete_file(self._api, source_kitchen, recipe_name,
                                         "delete file %s" % file_name, file_name)

        # add file in another path, with another name
        contents = 'renamed and moved file contents'
        recipe_dir_2, _ = self._add_new_file_in_remote(source_kitchen,
                                                       recipe_name,
                                                       os.path.join('resources', 'simple-file-new.txt'),
                                                       file_content=contents)

        # kitchen merge preview
        DKCloudCommandRunner.kitchen_merge_preview(self._api, source_kitchen, target_kitchen, True)

        # resolve conflicts
        file_path = os.path.join(recipe_name, file_name)
        home = expanduser('~')
        merge_dir = os.path.join(home, '.dk', 'test', 'merges')
        working_dir = os.path.join(merge_dir, '%s_to_%s' % (source_kitchen, target_kitchen))
        full_path = os.path.join(working_dir, file_path + '.base')
        resolved_contents = 'Resolved contents'
        DKFileHelper.write_file(full_path, resolved_contents)
        DKCloudCommandRunner.file_resolve(self._api, source_kitchen, target_kitchen, file_path)

        # kitchen merge
        rc = DKCloudCommandRunner.kitchen_merge(self._api, source_kitchen, target_kitchen)
        self.assertTrue(rc.ok())

        # check the kitchen states are as desired
        _, recipe_path = self._get_recipe_to_disk(target_kitchen, recipe_name)

        self.assertTrue(os.path.isfile(os.path.join(recipe_path, file_name)))
        after_merge_content_target = DKFileHelper.read_file(os.path.join(recipe_path, file_name))
        self.assertEqual(resolved_contents, after_merge_content_target)

        renamed_file = os.path.join(recipe_path, 'resources', 'simple-file-new.txt')
        self.assertTrue(os.path.isfile(renamed_file))
        renamed_file_contents = DKFileHelper.read_file(renamed_file)
        self.assertEqual(contents, renamed_file_contents)

        # cleanup
        if cleanup:
            self._delete_and_clean_kitchen(source_kitchen)
            self._delete_and_clean_kitchen(target_kitchen)

    # test when the remote to_kitchen has the resolved file deleted, after kitchen-merge-preview
    def test_merge_kitchens_remote_deleted_resolved(self):
        master_kitchen = 'CLI-Top'
        recipe_name = 'simple'
        file_name = 'simple-file.txt'
        from_kitchen, to_kitchen = self._setup_kitchens_for_merge(master_kitchen, recipe_name, file_name)

        # delete the resolved file in remote to_kitchen
        DKCloudCommandRunner.delete_file(self._api, to_kitchen, recipe_name, "delete description.json", file_name)

        # modify another file in remote to_kitchen
        self._update_file_in_remote(to_kitchen, recipe_name, "remote_modify_file.txt")

        # run kitchen-merge
        rc = DKCloudCommandRunner.kitchen_merge(self._api, from_kitchen, to_kitchen)
        self.assertFalse(rc.ok())
        expected_result = ('DKCloudCommandRunner Error.\n'
                           'Kitchen %s has new changes since last kitchen-merge-preview. Please run kitchen-merge-preview again.\n') % to_kitchen
        self.assertEqual(expected_result, rc.get_message())

        # deleted file should remain deleted after kitchen merge attempt
        _, recipe_path = self._get_recipe_to_disk(to_kitchen, recipe_name)
        self.assertFalse(os.path.isfile(os.path.join(recipe_path, file_name)))

    # test when the remote to_kitchen has new modifications on OK files, after kitchen-merge-preview
    def test_merge_kitchens_remote_modified_other(self):
        master_kitchen = 'CLI-Top'
        recipe_name = 'simple'
        file_name = 'simple-file.txt'
        from_kitchen, to_kitchen = self._setup_kitchens_for_merge(master_kitchen, recipe_name, file_name)

        # modify another file in remote to_kitchen
        another_file_name = 'remote_modify_file.txt'
        _, file_path = self._update_file_in_remote(to_kitchen, recipe_name, another_file_name)
        file_content_before = DKFileHelper.read_file(file_path)

        # run kitchen-merge
        rc = DKCloudCommandRunner.kitchen_merge(self._api, from_kitchen, to_kitchen)
        self.assertTrue(rc.ok())

        # the modified file should be intact after kitchen merge
        _, recipe_path = self._get_recipe_to_disk(to_kitchen, recipe_name)
        file_content_after = DKFileHelper.read_file(os.path.join(recipe_path, another_file_name))
        self.assertEqual(file_content_before.strip(), file_content_after.strip())

    # test when the remote to_kitchen has new files added, after kitchen-merge-preview
    def test_merge_kitchens_remote_new(self):
        master_kitchen = 'CLI-Top'
        recipe_name = 'simple'
        file_name = 'simple-file.txt'
        from_kitchen, to_kitchen = self._setup_kitchens_for_merge(master_kitchen, recipe_name, file_name)

        # add new file to remote to_kitchen
        new_file_name = 'new_file.txt'
        _, file_path = self._update_file_in_remote(to_kitchen, recipe_name, new_file_name)
        file_content_before = DKFileHelper.read_file(file_path)

        # run kitchen-merge
        rc = DKCloudCommandRunner.kitchen_merge(self._api, from_kitchen, to_kitchen)
        self.assertTrue(rc.ok())

        # new file should be intact after kitchen merge
        _, recipe_path = self._get_recipe_to_disk(to_kitchen, recipe_name)
        file_content_after = DKFileHelper.read_file(os.path.join(recipe_path, new_file_name))
        self.assertEqual(file_content_before.strip(), file_content_after.strip())

    # test when the remote to_kitchen has files deleted, after kitchen-merge-preview
    def test_merge_kitchens_remote_deleted_other(self):
        master_kitchen = 'CLI-Top'
        recipe_name = 'simple'
        file_name = 'simple-file.txt'
        from_kitchen, to_kitchen = self._setup_kitchens_for_merge(master_kitchen, recipe_name, file_name)

        # delete a file in remote to_kitchen
        delete_file_name = 'description.json'
        DKCloudCommandRunner.delete_file(self._api, to_kitchen, recipe_name, "delete description.json", delete_file_name)

        # run kitchen-merge
        rc = DKCloudCommandRunner.kitchen_merge(self._api, from_kitchen, to_kitchen)
        self.assertTrue(rc.ok())

        # deleted file should remain deleted after kitchen merge
        _, recipe_path = self._get_recipe_to_disk(to_kitchen, recipe_name)
        self.assertFalse(os.path.isfile(os.path.join(recipe_path, delete_file_name)))

    # test when the remote to_kitchen has files renamed to another recipe
    def test_merge_kitchens_remote_deleted_auto(self):
        # Create test_kitchen_parent from CLI-Top
        test_kitchen_parent = self._create_test_kitchen('CLI-Top')

        # test_kitchen_parent, recipe simple, Add 2 files
        recipe_simple = 'simple'
        file1 = os.path.normpath('resources/test-merge/file1.sql')
        file2 = os.path.normpath('resources/test-merge/file2.sql')
        _, r1_file1_path = self._update_file_in_remote(test_kitchen_parent, recipe_simple, file1)
        _, r1_file2_path = self._update_file_in_remote(test_kitchen_parent, recipe_simple, file2)

        # Create test_kitchen_child from test_kitchen_parent
        test_kitchen_child = self._create_test_kitchen(test_kitchen_parent)

        # test_kitchen_child, recipe simple, Add one file
        file3 = os.path.normpath('resources/file3.sql')
        _, r1_file3_path = self._update_file_in_remote(test_kitchen_child, recipe_simple, file3)

        # test_kitchen_parent, move files from recipe simple to simple2
        self._delete_file_in_remote(test_kitchen_parent, recipe_simple, file1)
        self._delete_file_in_remote(test_kitchen_parent, recipe_simple, file2)
        recipe_simple2 = 'simple2'
        _, r2_file1_path = self._update_file_in_remote(test_kitchen_parent, recipe_simple2, file1)
        _, r2_file2_path = self._update_file_in_remote(test_kitchen_parent, recipe_simple2, file2)

        # kmp -sk parent -tk child
        rc = DKCloudCommandRunner.kitchen_merge_preview(self._api, test_kitchen_parent, test_kitchen_child, True)
        self.assertTrue('Kitchen merge preview done.' in rc.get_message())
        self.assertTrue(rc.ok())

        # km -sk parent -tk child
        rc = DKCloudCommandRunner.kitchen_merge(self._api, test_kitchen_parent, test_kitchen_child)
        self.assertTrue(rc.ok())
        self.assertTrue('4 files changed, 2 insertions(+), 2 deletions(-)' in rc.get_message())
        merge_payload = rc.get_payload()
        self.assertIsNotNone(merge_payload)
        self.assertEqual('success', merge_payload['merge-kitchen-result']['status'])
        self.assertEqual(2, merge_payload['merge-kitchen-result']['merge_info']['stats']['deletions'])
        self.assertEqual(2, merge_payload['merge-kitchen-result']['merge_info']['stats']['additions'])
        self.assertEqual(4, merge_payload['merge-kitchen-result']['merge_info']['stats']['total'])
        self.assertEqual(201, merge_payload['merge-kitchen-result']['merge_info']['merge_status'])

    # test when the remote to_kitchen has files renamed to another recipe, manual merge case
    def test_merge_kitchens_remote_deleted_manual(self):
        # Create test_kitchen_parent from CLI-Top
        test_kitchen_parent = self._create_test_kitchen('CLI-Top')

        # test_kitchen_parent, recipe simple, Add 2 files
        recipe_simple = 'simple'
        file1 = os.path.normpath('resources/test-merge/file1.sql')
        file2 = os.path.normpath('resources/test-merge/file2.sql')
        _, r1_file1_path = self._update_file_in_remote(test_kitchen_parent, recipe_simple, file1)
        _, r1_file2_path = self._update_file_in_remote(test_kitchen_parent, recipe_simple, file2)

        # Create test_kitchen_child from test_kitchen_parent
        test_kitchen_child = self._create_test_kitchen(test_kitchen_parent)

        # test_kitchen_child, recipe simple, Add one file
        file3 = os.path.normpath('resources/file3.sql')
        _, r1_file3_path = self._update_file_in_remote(test_kitchen_child, recipe_simple, file3)

        # test_kitchen_parent, move files from recipe simple to simple2
        self._delete_file_in_remote(test_kitchen_parent, recipe_simple, file1)
        self._delete_file_in_remote(test_kitchen_parent, recipe_simple, file2)
        recipe_simple2 = 'simple2'
        _, r2_file1_path = self._update_file_in_remote(test_kitchen_parent, recipe_simple2, file1)
        _, r2_file2_path = self._update_file_in_remote(test_kitchen_parent, recipe_simple2, file2)

        # Modify file in parent
        file_name = 'simple-file.txt'
        contents = 'Parent contents'
        _, file_path_parent = self._update_file_in_remote(test_kitchen_parent, recipe_simple, file_name, file_content=contents)

        # Modify same file in child
        contents = 'Child contents'
        _, file_path_child = self._update_file_in_remote(test_kitchen_child, recipe_simple, file_name, file_content=contents)

        # resolve conflicts
        file_path = os.path.join(recipe_simple, file_name)
        home = expanduser('~')
        merge_dir = os.path.join(home, '.dk','test', 'merges')
        working_dir = os.path.join(merge_dir, '%s_to_%s' % (test_kitchen_parent, test_kitchen_child))
        full_path = os.path.join(working_dir, file_path + '.base')
        resolved_contents = '{\t\t\t"Resolved": \t\t\t"contents"}'
        resolved_formatted_contents = '{\n    "Resolved": "contents"\n}\n'
        DKFileHelper.write_file(full_path, resolved_contents)
        DKCloudCommandRunner.file_resolve(self._api, test_kitchen_parent, test_kitchen_child, file_path)

        # kmp -sk parent -tk child
        rc = DKCloudCommandRunner.kitchen_merge_preview(self._api, test_kitchen_parent, test_kitchen_child, False)
        self.assertTrue('Kitchen merge preview done.' in rc.get_message())
        self.assertTrue(rc.ok())

        # km -sk parent -tk child
        rc = DKCloudCommandRunner.kitchen_merge(self._api, test_kitchen_parent, test_kitchen_child)
        self.assertTrue(rc.ok())

        # check the kitchen states are as desired
        _, simple_recipe_path = self._get_recipe_to_disk(test_kitchen_child, recipe_simple)

        recipe1_simple_file_path = os.path.join(simple_recipe_path, 'simple-file.txt')
        self.assertTrue(os.path.isfile(recipe1_simple_file_path))
        after_merge_content_target = DKFileHelper.read_file(recipe1_simple_file_path)
        self.assertEqual(resolved_formatted_contents, after_merge_content_target)

        recipe1_file1_path = os.path.join(simple_recipe_path, file1)
        self.assertFalse(os.path.isfile(recipe1_file1_path))

        recipe1_file2_path = os.path.join(simple_recipe_path, file2)
        self.assertFalse(os.path.isfile(recipe1_file2_path))

        _, simple2_recipe_path = self._get_recipe_to_disk(test_kitchen_child, recipe_simple2)

        recipe2_file1_path = os.path.join(simple2_recipe_path, file1)
        self.assertTrue(os.path.isfile(recipe2_file1_path))

        recipe2_file2_path = os.path.join(simple2_recipe_path, file2)
        self.assertTrue(os.path.isfile(recipe2_file2_path))

    def test_merge_kitchens_success(self):
        existing_kitchen_name = 'master'
        base_test_kitchen_name = 'base-test-kitchen'
        branched_test_kitchen_name = 'branched-from-base-test-kitchen'
        base_test_kitchen_name = self._add_my_guid(base_test_kitchen_name)
        branched_test_kitchen_name = self._add_my_guid(branched_test_kitchen_name)

        # setup
        self._delete_and_clean_kitchen(branched_test_kitchen_name)
        self._delete_and_clean_kitchen(base_test_kitchen_name)
        # test
        # create base kitchen
        rs = DKCloudCommandRunner.create_kitchen(self._api, existing_kitchen_name, base_test_kitchen_name)
        self.assertTrue(rs.ok())
        # create branch kitchen from base kitchen
        rs = DKCloudCommandRunner.create_kitchen(self._api, base_test_kitchen_name, branched_test_kitchen_name)
        self.assertTrue(rs.ok())
        # do merge
        rd = DKCloudCommandRunner.merge_kitchens_improved(self._api, branched_test_kitchen_name, base_test_kitchen_name)
        self._check_no_merge_conflicts(rd)

        # cleanup
        self._delete_and_clean_kitchen(branched_test_kitchen_name)
        self._delete_and_clean_kitchen(base_test_kitchen_name)

    def test_merge_kitchens_improved_success(self):
        to_kitchen = 'dummy'
        from_kitchen = 'merge_success'

        mock_api = DKCloudAPIMock(self._cr_config)

        rv = DKCloudCommandRunner.merge_kitchens_improved(mock_api, from_kitchen, to_kitchen)
        self.assertTrue('1 files changed' in rv.get_message())
        self.assertTrue('1 insertions(+)' in rv.get_message())
        self.assertTrue('0 deletions(-)' in rv.get_message())
        # Check that the merge returned the diffs as expected.

    def test_merge_kitchens_ignore_files(self):
        orig_dir = os.getcwd()
        mock_api = DKCloudAPIMock(self._cr_config)

        kitchen_name = 'dummy_kitchen'
        temp_dir, kitchen_dir = self._make_kitchen_dir(kitchen_name, change_dir=False)

        os.chdir(kitchen_dir)
        for directory in ['.DS_Store', 'compiled-recipe']:
            os.mkdir(directory)

        DKCloudCommandRunner.update_local_recipes_with_remote(mock_api, temp_dir, kitchen_name)
        os.chdir(orig_dir)


    def test_print_test_results(self):
        # good for more than acive
        rdict = pickle.loads(open("files/completed_serving_rdict.p", "rb").read().replace('\r', ''))
        # rdict = pickle.load(open("files/completed_serving_rdict_eg.p", "rb"))
        rs = DKCloudCommandRunner._print_test_results(rdict)
        # look for some strings so you know it worked
        # but don't look for too much so the test breaks if we re-format
        print rs
        self.assertTrue('File' in rs)

    ''' FIXME AFF Alex fix in next ticket 
    def test_active_serving_watcher(self):
        # setup
        parent = 'master'
        kitchen = 'test_active_serving_watcher'
        kitchen = self._add_my_guid(kitchen)
        recipe_name = 'test-everything-recipe'
        variation_name = self._get_run_variation()
        self._delete_and_clean_kitchen(kitchen)

        rv = DKCloudCommandRunner.create_kitchen(self._api, parent, kitchen)
        self.assertTrue(rv.ok())

        # start watcher
        DKActiveServingWatcherSingleton().set_sleep_time(2)
        DKActiveServingWatcherSingleton().set_api(self._api)
        DKActiveServingWatcherSingleton().set_kitchen(kitchen)
        self.assertTrue(DKActiveServingWatcherSingleton().start_watcher())

        # cook one
        rs = DKCloudCommandRunner.create_order(self._api, kitchen, recipe_name, variation_name)
        self.assertTrue(rs.ok())
        wait_time = [.1, 1, 3, 3, 3, 3, 9, 18]
        found_active_serving = False
        wait_generator = (wt for wt in wait_time if found_active_serving is False)
        print 'test_active_serving_watcher: found_active_serving, trying ... '
        for wt in wait_generator:
            time.sleep(wt)
            resp1 = DKCloudCommandRunner.orderrun_detail(self._api, kitchen, {'summary': True})
            print 'test_active_serving_watcher: found_active_serving is False (%s)' % wt
            # print 'got', resp1.get_message()
            message = resp1.get_message()
            if resp1.ok():
                message_split = message.split('\n')
                if message_split is not None and len(message_split) > 10 and \
                        'ORDER RUN SUMMARY' in message_split[1] and \
                        'Order ID' in message_split[3] and 'DKRecipe#dk#test-everything-recipe#variation-test#' in message_split[3] and \
                        'Order Run ID' in message_split[4] and 'ct:' in message_split[4] and 'DKRecipe#dk#test-everything-recipe#variation-test#' in message_split[4] and \
                        'Status' in message_split[5] and 'COMPLETED_SERVING' in message_split[5]:
                    found_active_serving = True
        self.assertTrue(found_active_serving)

        # cleanup
        self._delete_and_clean_kitchen(kitchen)
    '''

    def test_user_info(self):
        rc = DKCloudCommandRunner.user_info(self._api)
        self.assertTrue(rc.ok())

    def test_order_list(self):
        parent_kitchen = 'CLI-Top'
        recipe_name = 'parallel-recipe-test'
        variation_name = self._get_run_variation_for_recipe(recipe_name)
        new_kitchen = 'test_order_list'
        new_kitchen = self._add_my_guid(new_kitchen)
        self._delete_and_clean_kitchen(new_kitchen)
        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, new_kitchen)
        self.assertTrue(rs.ok())

        rs = DKCloudCommandRunner.create_order(self._api, new_kitchen, recipe_name, variation_name)
        new_order_id_1 = rs.get_payload()['serving_hid']
        self.assertTrue(rs.ok())

        rs = DKCloudCommandRunner.list_order(self._api, new_kitchen)
        output_string = rs.rc['message']
        self.assertTrue(new_order_id_1 in output_string)

        found_completed_serving = False
        wait_time = [.2, .5, .5, .5, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 10, 10]
        for wt in wait_time:
            rs = DKCloudCommandRunner.list_order(self._api, new_kitchen)
            output_string = rs.rc['message']
            n = output_string.count(new_order_id_1)
            if n == 1 and ('OrderRun Completed' in output_string):
                found_completed_serving = True
                break
            time.sleep(wt)
        self.assertTrue(found_completed_serving)
        # cleanup
        self._delete_and_clean_kitchen(new_kitchen)

    def test_order_list_for_repeating_order(self):
        parent_kitchen = 'master'
        recipe_name = 'parallel-recipe-test'
        variation_name = self._get_run_variation_for_recipe(recipe_name, repeater=True)
        new_kitchen = 'test_order_list_for_repeating_order'
        new_kitchen = self._add_my_guid(new_kitchen)
        self._delete_and_clean_kitchen(new_kitchen)
        rs = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, new_kitchen)
        self.assertTrue(rs.ok())

        rs = DKCloudCommandRunner.create_order(self._api, new_kitchen, recipe_name, variation_name)
        new_order_id_1 = rs.get_payload()['serving_hid']
        self.assertTrue(rs.ok())

        found_completed_serving = False
        wait_time = [10,61,61,61,61,61,61,61]
        for wt in wait_time:
            rs = DKCloudCommandRunner.list_order(self._api, new_kitchen)
            output_string = rs.rc['message']

            output_string_split = output_string.split('\n')

            index = 0
            output_string_split_length = len(output_string_split)

            generic_pattern_title = 'ORDER SUMMARY (order ID:'

            find_title = False
            pattern_title = 'ORDER SUMMARY (order ID: %s)' % new_order_id_1
            while not find_title and index < output_string_split_length:
                if pattern_title in output_string_split[index]:
                    find_title = True
                index += 1

            find_order_run_1 = False
            pattern_order_run_1a = '1.  ORDER RUN	(OrderRun ID:'
            while not find_order_run_1 and index < output_string_split_length:
                if generic_pattern_title not in output_string_split[index] and \
                                pattern_order_run_1a in output_string_split[index] and \
                                index + 1 < output_string_split_length and \
                                'OrderRun Completed' in output_string_split[index+1]:
                    find_order_run_1 = True
                index += 1

            find_order_run_2 = False
            pattern_order_run_2a = '2.  ORDER RUN	(OrderRun ID:'
            while not find_order_run_2 and index < output_string_split_length:
                if generic_pattern_title not in output_string_split[index] and \
                        pattern_order_run_2a in output_string_split[index] and \
                                index + 1 < output_string_split_length and \
                                'OrderRun Completed' in output_string_split[index+1]:
                    find_order_run_2 = True
                index += 1

            if find_title and find_order_run_1 and find_order_run_2:
                found_completed_serving = True
                break

            time.sleep(wt)

        self.assertTrue(found_completed_serving)

        # cleanup
        self._delete_and_clean_kitchen(new_kitchen)

    def test_order_list_with_filters(self):
        parent_kitchen = 'CLI-Top'
        # Don't use a guid for this. Don't
        kitchen = self._add_my_guid('test_order_list_with_filters')
        recipe1 = 'parallel-recipe-test'
        recipe1_variation = self._get_run_variation_for_recipe(recipe1)
        recipe2 = 'simple'
        recipe2_variation = 'simple-variation-now'

        setup = True
        if setup:
            self._delete_and_clean_kitchen(kitchen)
            rv = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, kitchen)
            self.assertTrue(rv.ok())

        rv = DKCloudCommandRunner.create_order(self._api, kitchen, recipe1, recipe1_variation)
        self.assertTrue(rv.ok())
        first_order = rv.get_payload()
        rv = DKCloudCommandRunner.create_order(self._api, kitchen, recipe1, recipe1_variation)
        self.assertTrue(rv.ok())

        time.sleep(20)

        rs = DKCloudCommandRunner.list_order(self._api, kitchen)
        self.assertTrue(rs.ok())
        message = rs.rc['message']
        self.assertTrue(
            'OrderRun is Planned' in message or 'OrderRun Completed' in message or 'OrderRun is Active' in message)

        # cleanup
        self._delete_and_clean_kitchen(kitchen)

    def test_orderrun_delete(self):
        kitchen = 'myKitchen'
        mock_api = DKCloudAPIMock(self._cr_config)
        rs = DKCloudCommandRunner.delete_orderrun(mock_api, kitchen, 'good')
        self.assertTrue(rs.ok())

        rs = DKCloudCommandRunner.delete_orderrun(mock_api, kitchen, 'bad')
        self.assertFalse(rs.ok())

    def test_kitchen_config(self):
        parent_kitchen = 'CLI-Top'
        child_kitchen = self._add_my_guid('modify_kitchen_settings_runner')

        setup = True
        if setup:
            self._delete_and_clean_kitchen(child_kitchen)
            rv = DKCloudCommandRunner.create_kitchen(self._api, parent_kitchen, child_kitchen)
            self.assertTrue(rv.ok())

        add = (('newvar1', 'newval1'),)
        unset = ('newvar1')
        get = ('newvar1')
        listall = True
        rs = DKCloudCommandRunner.config_kitchen(self._api, child_kitchen, add=add)
        self.assertTrue(rs.ok())
        payload = rs.get_payload()
        self.assertIsNotNone(payload)
        message = rs.get_message()
        self.assertTrue('newvar1 added' in message)

        rs = DKCloudCommandRunner.config_kitchen(self._api, child_kitchen, get=get)
        self.assertTrue(rs.ok())
        payload = rs.get_payload()
        self.assertIsNotNone(payload)
        message = rs.get_message()
        self.assertTrue(message == 'newval1\n')

        rs = DKCloudCommandRunner.config_kitchen(self._api, child_kitchen, unset=unset)
        self.assertTrue(rs.ok())
        payload = rs.get_payload()
        self.assertIsNotNone(payload)
        message = rs.get_message()

        rs = DKCloudCommandRunner.config_kitchen(self._api, child_kitchen, listall=listall)
        self.assertTrue(rs.ok())
        payload = rs.get_payload()
        self.assertIsNotNone(payload)
        message = rs.get_message()
        self.assertTrue('newvar1' not in message)

        cleanup = False
        if cleanup:
            self._delete_and_clean_kitchen(child_kitchen)

    # helpers ---------------------------------
    def _check_no_merge_conflicts(self, resp):
        self.assertTrue(str(resp).find('diverged') < 0)

    def _get_recipe_file(self, kitchen, recipe_name, file_path, file_name, temp_dir=None):
        delete_temp_dir = td = False
        if temp_dir is None:
            td, kitchen_dir = self._make_kitchen_dir(kitchen, change_dir=False)
            delete_temp_dir = True
        else:
            kitchen_dir = temp_dir
        rs = DKCloudCommandRunner.get_recipe(self._api, kitchen, recipe_name, kitchen_dir)
        self.assertTrue(rs.ok())
        the_path = os.path.join(kitchen_dir, os.path.join(file_path, file_name))
        if os.path.isfile(the_path):
            with open(the_path, 'r') as rfile:
                rfile.seek(0)
                the_file = rfile.read()
            rc = the_file
        else:
            rc = None
        if delete_temp_dir is True:
            shutil.rmtree(td, ignore_errors=True)
        return rc

    def _get_recipe(self, kitchen, recipe):
        rs = DKCloudCommandRunner.get_recipe(self._api, kitchen, recipe)
        self.assertTrue(rs.ok())
        return True

    def _get_file_sha(self, kitchen_dir, recipe_name):
        recipe_meta_dir = os.path.join(kitchen_dir, '.dk', 'recipes', recipe_name)
        self.assertTrue(os.path.exists(recipe_meta_dir))
        file_content = DKFileHelper.read_file(os.path.join(recipe_meta_dir, 'FILE_SHA'))
        file_shas = dict()
        for line in file_content.splitlines():
            file_path, file_sha = line.strip().split(':')
            file_shas[file_path] = file_sha
        return file_shas

    def _setup_kitchens_for_merge(self, master_kitchen, recipe_name, file_name):
        from_kitchen = self._create_test_kitchen(master_kitchen)
        to_kitchen = self._create_test_kitchen(master_kitchen)

        # update file in both kitchens, then run kitchen-merge-preview
        self._update_file_in_remote(from_kitchen, recipe_name, file_name)
        self._update_file_in_remote(to_kitchen, recipe_name, file_name)
        DKCloudCommandRunner.kitchen_merge_preview(self._api, from_kitchen, to_kitchen, True)

        # resolve conflicts
        file_path = "%s/%s" % (recipe_name, file_name)
        DKCloudCommandRunner.file_resolve(self._api, from_kitchen, to_kitchen, file_path)

        return from_kitchen, to_kitchen


def add_new_file_in_local(recipe_dir, file_name):
    return update_file_in_local(recipe_dir, file_name)


def update_file_in_local(recipe_dir, file_name):
    file_path = os.path.join(recipe_dir, file_name)
    with open(file_path, 'w') as f:
        f.write('now it %s' % time.time())
    return file_path


def delete_file_in_local(recipe_dir, file_name):
    file_path = os.path.join(recipe_dir, file_name)
    os.remove(file_path)
    return file_path


def get_total_files(file_path):
    return sum([len(files) for r, d, files in os.walk(file_path)])


if __name__ == '__main__':
    unittest.main()
