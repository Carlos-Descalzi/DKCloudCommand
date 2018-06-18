import unittest
from DKPathHelper import DKPathHelper


class DKCommonUnitTestSettings(unittest.TestCase):
    if DKPathHelper.is_windows_os():
        _TEMPFILE_LOCATION = 'c:\\temp'
    else:
        _TEMPFILE_LOCATION = '/var/tmp'
