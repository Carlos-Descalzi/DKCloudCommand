import unittest
import os
import shutil
import json
from DKPathHelper import DKPathHelper

from DKCloudCommand.modules.DKFileHelper import DKFileHelper
from DKCloudCommandConfig import DKCloudCommandConfig

__author__ = 'DataKitchen, Inc.'


class TestDKCloudCommandConfig(unittest.TestCase):
    if DKPathHelper.is_windows_os():
        _TEMPFILE_LOCATION = 'c:\\temp\\TestDKCloudCommandConfig'
    else:
        _TEMPFILE_LOCATION = '/var/tmp/TestDKCloudCommandConfig'

    def setUp(self):
        pass

    def tearDown(self):
        shutil.rmtree(self._TEMPFILE_LOCATION, ignore_errors=True)

    def test_get_latest_version_from_pip(self):
        cfg = DKCloudCommandConfig()
        try:
            latest_version_from_pip = cfg.get_latest_version_from_pip()
            self.assertIsNotNone(latest_version_from_pip)
            dot_count = latest_version_from_pip.count(".")
            self.assertTrue(dot_count > 1)
        except:
            self.assertTrue(False, 'Error getting latest version config from pip')

    def test_read_config_from_disk(self):
        cfg = DKCloudCommandConfig()
        cfg.set_dk_temp_folder(self._TEMPFILE_LOCATION)
        cfg.set_dk_customer_temp_folder(self._TEMPFILE_LOCATION)
        cfg.init_from_file("files/UnitTestConfig.json")
        self.assertEquals(cfg.get_port(), u'00')
        self.assertEquals(cfg.get_password(), u'shhh')
        self.assertEquals(cfg.get_username(), u'a@b.c')
        self.assertEquals(cfg.get_ip(), u'IP')
        self.assertTrue(cfg.get_config_file_location())  # make sure absolute location get saved
        pass

    def test_save_config_from_disk(self):
        cfg = DKCloudCommandConfig()
        cfg.set_dk_temp_folder(self._TEMPFILE_LOCATION)
        cfg.set_dk_customer_temp_folder(self._TEMPFILE_LOCATION)
        cfg.init_from_file("files/UnitTestConfig.json")
        cfg.set_jwt('newTokenForYou')
        self.assertTrue(cfg.get_jwt(), 'newTokenForYou')
        pass

    def test_general_config_file(self):
        cfg = DKCloudCommandConfig()
        cfg.set_dk_temp_folder(self._TEMPFILE_LOCATION)
        self.assertFalse(cfg.is_general_config_file_configured())

        general_config_path = os.path.join(self._TEMPFILE_LOCATION, DKCloudCommandConfig.GENERAL_CONFIG_FILE_NAME)
        general_config_contents = """{
                "dk-cloud-merge-tool": "meld {{left}} {{base}} {{right}}", 
                "dk-check-working-path": true, 
                "dk-cloud-diff-tool": "meld {{local}} {{remote}}"
            }"""
        DKFileHelper.write_file(general_config_path, general_config_contents)
        self.assertTrue(cfg.is_general_config_file_configured())

        self.assertEqual(general_config_path, cfg.get_general_config_file_location())

        merge_tool = 'my merge tool'
        diff_tool = 'my diff tool'
        check_working_path = 'true'
        hide_context_legend = 'false'
        skip_recipe_checker = 'true'
        cfg.configure_general_file(merge_tool, diff_tool, check_working_path, hide_context_legend, skip_recipe_checker)

        self.assertTrue(cfg.is_general_config_file_configured())
        general_config_path = os.path.join(self._TEMPFILE_LOCATION, DKCloudCommandConfig.GENERAL_CONFIG_FILE_NAME)
        general_config_contents = DKFileHelper.read_file(general_config_path)
        general_config_dict = json.loads(general_config_contents)

        self.assertEqual(5, len(general_config_dict))

        self.assertTrue(DKCloudCommandConfig.DK_CHECK_WORKING_PATH in general_config_dict)
        self.assertTrue(DKCloudCommandConfig.DK_CLOUD_DIFF_TOOL in general_config_dict)
        self.assertTrue(DKCloudCommandConfig.DK_CLOUD_MERGE_TOOL in general_config_dict)
        self.assertTrue(DKCloudCommandConfig.DK_HIDE_CONTEXT_LEGEND in general_config_dict)

        self.assertEqual('true', general_config_dict[DKCloudCommandConfig.DK_CHECK_WORKING_PATH])
        self.assertEqual(diff_tool, general_config_dict[DKCloudCommandConfig.DK_CLOUD_DIFF_TOOL])
        self.assertEqual(merge_tool, general_config_dict[DKCloudCommandConfig.DK_CLOUD_MERGE_TOOL])
        self.assertEqual('false', general_config_dict[DKCloudCommandConfig.DK_HIDE_CONTEXT_LEGEND])

    def test_init_general_config(self):
        cfg = DKCloudCommandConfig()
        cfg.set_dk_temp_folder(self._TEMPFILE_LOCATION)
        self.assertFalse(cfg.is_general_config_file_configured())

        general_config_path = os.path.join(self._TEMPFILE_LOCATION, DKCloudCommandConfig.GENERAL_CONFIG_FILE_NAME)
        general_config_contents = """{
                "dk-cloud-merge-tool": "meld {{left}} {{base}} {{right}}", 
                "dk-check-working-path": true, 
                "dk-cloud-diff-tool": "meld {{local}} {{remote}}"
            }"""
        DKFileHelper.write_file(general_config_path, general_config_contents)

        self.assertIsNotNone(cfg._config_dict)
        self.assertEquals(0, len(cfg._config_dict))

        cfg.init_general_config()
        self.assertIsNotNone(cfg._config_dict)
        self.assertEquals(3, len(cfg._config_dict))

        self.assertTrue(DKCloudCommandConfig.DK_CHECK_WORKING_PATH in cfg._config_dict)
        self.assertTrue(DKCloudCommandConfig.DK_CLOUD_DIFF_TOOL in cfg._config_dict)
        self.assertTrue(DKCloudCommandConfig.DK_CLOUD_MERGE_TOOL in cfg._config_dict)

        self.assertTrue(cfg._config_dict[DKCloudCommandConfig.DK_CHECK_WORKING_PATH])
        self.assertEqual('meld {{local}} {{remote}}', cfg._config_dict[DKCloudCommandConfig.DK_CLOUD_DIFF_TOOL])
        self.assertEqual('meld {{left}} {{base}} {{right}}', cfg._config_dict[DKCloudCommandConfig.DK_CLOUD_MERGE_TOOL])

    def test_context(self):
        cfg = DKCloudCommandConfig()
        cfg.set_dk_temp_folder(self._TEMPFILE_LOCATION)

        os.mkdir(self._TEMPFILE_LOCATION)

        # context list
        os.mkdir(os.path.join(self._TEMPFILE_LOCATION, 'context1'))
        os.mkdir(os.path.join(self._TEMPFILE_LOCATION, 'context2'))
        os.mkdir(os.path.join(self._TEMPFILE_LOCATION, 'context3'))
        os.mkdir(os.path.join(self._TEMPFILE_LOCATION, 'context4'))

        context_list = cfg.context_list()

        self.assertIsNotNone(context_list)
        self.assertEquals(4, len(context_list))
        self.assertTrue('context1' in context_list)
        self.assertTrue('context2' in context_list)
        self.assertTrue('context3' in context_list)
        self.assertTrue('context4' in context_list)

        # set and get context
        cfg.set_context('context3')
        current_context = cfg.get_current_context()
        self.assertEquals('context3', current_context)

        # delete_context
        self.assertTrue(cfg.context_exists('context3'))
        cfg.delete_context('context3')
        self.assertFalse(cfg.context_exists('context3'))

        # create context
        cfg.create_context('context5')

        context_list = cfg.context_list()

        self.assertIsNotNone(context_list)
        self.assertEquals(4, len(context_list))
        self.assertTrue('context1' in context_list)
        self.assertTrue('context2' in context_list)
        self.assertTrue('context4' in context_list)
        self.assertTrue('context5' in context_list)

        # switch context
        dk_context_path = os.path.join(cfg.get_dk_temp_folder(), '.context')

        cfg.switch_context('context2')
        dk_context = DKFileHelper.read_file(dk_context_path)
        self.assertEquals('context2', dk_context)

        cfg.switch_context('context3')
        dk_context = DKFileHelper.read_file(dk_context_path)
        self.assertEquals('context3', dk_context)

        # token save
        dk_customer_temp_folder = os.path.join(cfg.get_dk_temp_folder(), 'context3')
        cfg.set_dk_customer_temp_folder(dk_customer_temp_folder)
        cfg.set_jwt('my-test-jwt')

        cfg.save_jwt_to_file()

        self.assertEquals(os.path.join(dk_customer_temp_folder, 'config.json'), cfg.get_config_file_location())

        self.assertEquals(dk_customer_temp_folder, cfg.get_dk_customer_temp_folder())
        self.assertEquals('my-test-jwt', cfg.get_jwt())


if __name__ == '__main__':
    unittest.main()
