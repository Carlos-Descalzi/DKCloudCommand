import shutil
import unittest

import os
from BaseTestCloud import BaseTestCloud
from DKCloudCommandRunner import DKCloudCommandRunner


class TestUnicode(BaseTestCloud):

    def setUp(self):
        super(TestUnicode, self).setUp()
        self._kitchens = list()
        self._tmpdirs = list()

    def tearDown(self):
        for kitchen in self._kitchens:
            print "delete kitchen %s" % kitchen
            self._delete_and_clean_kitchen(kitchen)
        for tmpdir in self._tmpdirs:
            print "delete tmp dir %s" % tmpdir
            shutil.rmtree(tmpdir, ignore_errors=True)
        super(TestUnicode, self).tearDown()

    def test_recipe_get_remote_new(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'
        temp_dir, recipe_dir_1 = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # add a new file with unicode in remote
        file_name = "remote_new_unicode_file.txt"
        file_content = u'\u6d4b\u8bd5'
        recipe_dir_2, _ = self._add_new_file_in_remote(kitchen_name, recipe_name, file_name, file_content=file_content)

        # run recipe-get in recipe_dir_1
        rc = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name, start_dir=recipe_dir_1, yes=True)
        self.assertTrue(rc.ok())
        self.assertEqual(u'1 new or missing files from remote:\n\t%s\n' % file_name, rc.get_message())

        # check remote_new_unicode_file.txt is added in recipe_dir_1
        with open(os.path.join(recipe_dir_1, file_name), 'r') as f:
            read_content = f.read()
            self.assertEqual(file_content, read_content.decode('utf-8'))

    def test_recipe_get_remote_modified_no_conflict(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'
        temp_dir, recipe_dir_1 = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # update file with unicode in remote
        file_name = "remote_and_local_modify.txt"
        file_content = u'\u6d4b\u8bd5'
        self._update_file_in_remote(kitchen_name, recipe_name, file_name, file_content=file_content)

        # recipe-get in recipe_dir_1
        rc = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name, start_dir=recipe_dir_1, yes=True)
        self.assertTrue(rc.ok())
        self.assertEqual(u"Auto-merging '%s'\n\n" % file_name, rc.get_message())

        # check remote_new_unicode_file.txt is added in recipe_dir_1
        with open(os.path.join(recipe_dir_1, file_name), 'r') as f:
            read_content = f.read()
            self.assertEqual("Dummy data\n%s" % file_content, read_content.decode('utf-8'))

    def test_recipe_get_remote_modified_conflict(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'
        temp_dir, recipe_dir_1 = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # update file with unicode in remote
        file_name = "remote_and_local_modify.txt"
        remote_new_line = u'\u6d4b\u8bd5'
        self._update_file_in_remote(kitchen_name, recipe_name, file_name, file_content=remote_new_line)

        # update file in local
        local_new_line = u'\u4e0a\u5e02\u516c\u53f8'
        self._update_file_in_local(recipe_dir_1, file_name, file_content=local_new_line)

        # recipe-get in recipe_dir_1
        rc = DKCloudCommandRunner.get_recipe(self._api, kitchen_name, recipe_name, start_dir=recipe_dir_1, yes=True)
        self.assertTrue(rc.ok())
        self.assertEqual(u"Auto-merging '%s'\nCONFLICT (content): Merge conflict in %s\n\n" % (file_name, file_name), rc.get_message())

        # check remote_new_unicode_file.txt is added in recipe_dir_1
        with open(os.path.join(recipe_dir_1, file_name), 'r') as f:
            read_content = f.read()
            self.assertEqual("<<<<<<< your %s\n%s=======\nDummy data\n%s>>>>>>> their %s\n" % (file_name, local_new_line, remote_new_line, file_name), read_content.decode('utf-8'))

    def test_recipe_update(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'
        temp_dir, recipe_dir_1 = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # update file in local
        file_name = 'local_modify_file.txt'
        local_new_line = u'\u4e0a\u5e02\u516c\u53f8'
        self._update_file_in_local(recipe_dir_1, file_name, file_content=local_new_line)

        rc = DKCloudCommandRunner.update_all_files(self._api, kitchen_name, recipe_name, recipe_dir_1, "add unicode")
        self.assertTrue(rc.ok())
        self.assertEqual(u'Update results:\n\nNew files:\n\tNone\nUpdated files:\n\t%s\nDeleted files:\n\tNone\n\nIssues:\n\nNo issues found' % file_name, rc.get_message())

        # check file is indeed modified
        _, recipe_dir_2 = self._get_recipe_to_disk(kitchen_name, recipe_name)
        with open(os.path.join(recipe_dir_2, file_name)) as f:
            read_content = f.read()
            self.assertEqual(local_new_line, read_content.decode('utf-8'))

    def test_file_update(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'
        temp_dir, recipe_dir_1 = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # update file in local
        file_name = 'local_modify_file.txt'
        local_new_line = u'\u4e0a\u5e02\u516c\u53f8'
        self._update_file_in_local(recipe_dir_1, file_name, file_content=local_new_line)

        os.chdir(recipe_dir_1)
        rc = DKCloudCommandRunner.update_file(self._api, kitchen_name, recipe_name, recipe_dir_1, "add unicode", file_name)
        self.assertTrue(rc.ok())
        self.assertEqual('DKCloudCommand.update_file for %s succeeded' % file_name, rc.get_message())

        # check file is indeed modified
        _, recipe_dir_2 = self._get_recipe_to_disk(kitchen_name, recipe_name)
        with open(os.path.join(recipe_dir_2, file_name)) as f:
            read_content = f.read()
            self.assertEqual(local_new_line, read_content.decode('utf-8'))

    def test_file_diff(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'
        temp_dir, recipe_dir_1 = self._get_recipe_to_disk(kitchen_name, recipe_name)

        # update file in local
        file_name = 'local_modify_file.txt'
        local_new_line = u'\u4e0a\u5e02\u516c\u53f8'
        self._update_file_in_local(recipe_dir_1, file_name, file_content=local_new_line)

        os.chdir(recipe_dir_1)
        rc = DKCloudCommandRunner.file_diff(self._api, kitchen_name, recipe_name, recipe_dir_1, file_name)
        print rc
        self.assertTrue(rc.ok())
        self.assertEqual("File diff done.", rc.get_message())

    def test_file_get(self):
        kitchen_name = self._create_test_kitchen('CLI-Top')
        recipe_name = 'simple'
        temp_dir, recipe_dir_1 = self._get_recipe_to_disk(kitchen_name, recipe_name)

        file_name = 'remote_and_local_modify.txt'
        # update file in remote
        remote_new_line = u'\u6d4b\u8bd5'
        self._update_file_in_remote(kitchen_name, recipe_name, file_name, file_content=remote_new_line)

        # update file in local
        local_new_line = u'\u4e0a\u5e02\u516c\u53f8'
        self._update_file_in_local(recipe_dir_1, file_name, file_content=local_new_line)

        os.chdir(recipe_dir_1)
        rc = DKCloudCommandRunner.get_file(self._api, kitchen_name, recipe_name, file_name)
        self.assertTrue(rc.ok())
        self.assertEqual('DKCloudCommand.get_recipe for %s success' % file_name, rc.get_message())

        with open(os.path.join(recipe_dir_1, file_name)) as f:
            read_content = f.read()
            self.assertEqual("Dummy data\n%s" % remote_new_line, read_content.decode('utf-8'))

if __name__ == '__main__':
    unittest.main()
