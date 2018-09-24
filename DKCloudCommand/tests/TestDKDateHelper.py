import unittest
import shutil
from datetime import datetime
import time
import pytz
from DKPathHelper import DKPathHelper
from DKCommonUnitTestSettings import DKCommonUnitTestSettings
from DKDateHelper import DKDateHelper


class TestDKDateHelper(DKCommonUnitTestSettings):
    _TEMP_FILE_LOCATION = '/var/tmp'

    def setUp(self):
        self.temp_dir = None
        if DKPathHelper.is_windows_os():
            TestDKDateHelper._TEMP_FILE_LOCATION = 'c:\\temp'
        else:
            TestDKDateHelper._TEMP_FILE_LOCATION = '/var/tmp'

    def tearDown(self):
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_format_timestamp_basic_path(self):
        utc = pytz.utc
        my_date = datetime(2002, 5, 17, hour=16, minute=17, second=18, microsecond=19,tzinfo=utc)
        my_date_timestamp = time.mktime(my_date.timetuple())
        my_date_timestamp_coming_from_backend = long(my_date_timestamp * 1000)
        result = DKDateHelper.format_timestamp(my_date_timestamp_coming_from_backend)
        self.assertTrue('2002-05-17 'in result)
        self.assertTrue(':17:18 ' in result)

    def test_format_timestamp_none(self):
        result = DKDateHelper.format_timestamp(None)
        self.assertEquals('Not available - None', result)

    def test_format_timestamp_bad_format(self):
        result = DKDateHelper.format_timestamp('hello')
        self.assertEquals('Not available - bad format: hello', result)

    def test_format_timing_basic_path(self):
        value = 553520000
        result = DKDateHelper.format_timing(value)
        self.assertTrue('153:45:20', result)

    def test_format_timing_none(self):
        result = DKDateHelper.format_timing(None)
        self.assertEquals('Not available - None', result)

    def test_format_timing_bad_format(self):
        result = DKDateHelper.format_timing('hello')
        self.assertEquals('Not available - bad format: hello', result)


if __name__ == '__main__':
    unittest.main()
