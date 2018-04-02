import unittest
import sys
import os
from datetime import datetime

from DKCloudCommandConfig import DKCloudCommandConfig

__author__ = 'DataKitchen, Inc.'


class TestDKCloudCommandConfig(unittest.TestCase):
    _TEMPFILE_LOCATION = '/var/tmp'

    def test_read_config_from_disk(self):
        cfg = DKCloudCommandConfig()
        cfg.set_dk_temp_folder(self._TEMPFILE_LOCATION)
        cfg.init_from_file("files/UnitTestConfig.json")
        self.assertEquals(cfg.get_port(), u'00')
        self.assertEquals(cfg.get_password(), u'shhh')
        self.assertEquals(cfg.get_username(), u'a@b.c')
        self.assertEquals(cfg.get_ip(), u'IP')
        self.assertTrue(cfg.get_file_location())  # make sure absolute location get saved
        pass

    def test_save_config_from_disk(self):
        cfg = DKCloudCommandConfig()
        cfg.set_dk_temp_folder(self._TEMPFILE_LOCATION)
        cfg.init_from_file("../DKCloudCommandConfig.json")
        cfg.set_jwt('newTokenForYou')
        self.assertTrue(cfg.get_jwt(), 'newTokenForYou')
        pass


if __name__ == '__main__':
    unittest.main()
