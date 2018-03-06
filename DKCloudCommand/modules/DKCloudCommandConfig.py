import json
import os

__author__ = 'DataKitchen, Inc.'


class DKCloudCommandConfig(object):
    _config_dict = dict()
    _config_attributes = None
    DK_CLOUD_PORT = 'dk-cloud-port'
    DK_CLOUD_IP = 'dk-cloud-ip'
    DK_CLOUD_USERNAME = 'dk-cloud-username'
    DK_CLOUD_PASSWORD = 'dk-cloud-password'
    DK_CLOUD_JWT = 'dk-cloud-jwt'
    DK_CLOUD_FILE_LOCATION = 'dk-cloud-file-location'
    DK_CLOUD_MERGE_TOOL = 'dk-cloud-merge-tool'
    DK_CLOUD_DIFF_TOOL = 'dk-cloud-diff-tool'
    MERGE_DIR = 'merges'
    DIFF_DIR = 'diffs'

    def __init__(self):
        self._dk_temp_folder = None
        if self._config_dict is None:
            self._config_dict = dict()
        self._required_config_attributes = [DKCloudCommandConfig.DK_CLOUD_PORT,
                                            DKCloudCommandConfig.DK_CLOUD_IP,
                                            DKCloudCommandConfig.DK_CLOUD_USERNAME,
                                            DKCloudCommandConfig.DK_CLOUD_PASSWORD]

    def __str__(self):
        output_string = 'Username:\t\t%s\n' % self._config_dict[DKCloudCommandConfig.DK_CLOUD_USERNAME]
        output_string += 'Password:\t\t%s\n' % self._config_dict[DKCloudCommandConfig.DK_CLOUD_PASSWORD]
        output_string += 'Cloud IP:\t\t%s\n' % self._config_dict[DKCloudCommandConfig.DK_CLOUD_IP]
        output_string += 'Cloud Port:\t\t%s\n' % self._config_dict[DKCloudCommandConfig.DK_CLOUD_PORT]
        output_string += 'Cloud File Location:\t%s\n' % self._config_dict[DKCloudCommandConfig.DK_CLOUD_FILE_LOCATION]
        output_string += 'Merge Tool:\t\t%s\n' % self._config_dict[DKCloudCommandConfig.DK_CLOUD_MERGE_TOOL]
        output_string += 'Diff Tool:\t\t%s\n' % self._config_dict[DKCloudCommandConfig.DK_CLOUD_DIFF_TOOL]
        return output_string

    def get_ip(self):
        if DKCloudCommandConfig.DK_CLOUD_IP in self._config_dict:
            return self._config_dict[DKCloudCommandConfig.DK_CLOUD_IP]
        else:
            return False

    def get_port(self):
        if DKCloudCommandConfig.DK_CLOUD_PORT in self._config_dict:
            return self._config_dict[DKCloudCommandConfig.DK_CLOUD_PORT]
        else:
            return False

    def get_username(self):
        if DKCloudCommandConfig.DK_CLOUD_USERNAME in self._config_dict:
            return self._config_dict[DKCloudCommandConfig.DK_CLOUD_USERNAME]
        else:
            return False

    def get_password(self):
        if DKCloudCommandConfig.DK_CLOUD_PASSWORD in self._config_dict:
            return self._config_dict[DKCloudCommandConfig.DK_CLOUD_PASSWORD]
        else:
            return False

    def get_jwt(self):
        if DKCloudCommandConfig.DK_CLOUD_JWT in self._config_dict:
            return self._config_dict[DKCloudCommandConfig.DK_CLOUD_JWT]
        else:
            return None

    def set_jwt(self, jwt=None):
        if jwt is not None:
            self._config_dict[DKCloudCommandConfig.DK_CLOUD_JWT] = jwt
            return True
        else:
            return False

    def delete_jwt(self):
        if DKCloudCommandConfig.DK_CLOUD_JWT in self._config_dict:
            del self._config_dict[DKCloudCommandConfig.DK_CLOUD_JWT]

    def set_file_location(self, loc=None):
        if loc is not None:
            self._config_dict[DKCloudCommandConfig.DK_CLOUD_FILE_LOCATION] = loc
            return True
        else:
            return False

    def get_file_location(self):
        if DKCloudCommandConfig.DK_CLOUD_FILE_LOCATION in self._config_dict:
            return self._config_dict[DKCloudCommandConfig.DK_CLOUD_FILE_LOCATION]
        else:
            return False

    def get_merge_tool(self):
        if DKCloudCommandConfig.DK_CLOUD_MERGE_TOOL not in self._config_dict or \
                self._config_dict[DKCloudCommandConfig.DK_CLOUD_MERGE_TOOL] is None or \
                self._config_dict[DKCloudCommandConfig.DK_CLOUD_MERGE_TOOL] is None:
            raise Exception('Merge tool was not properly configured. Please run \'dk config-list\' to check current\
                configuration and \'dk config\' to change it.')
        return self._config_dict[DKCloudCommandConfig.DK_CLOUD_MERGE_TOOL]

    def get_diff_tool(self):
        if DKCloudCommandConfig.DK_CLOUD_DIFF_TOOL not in self._config_dict or \
                self._config_dict[DKCloudCommandConfig.DK_CLOUD_DIFF_TOOL] is None or \
                self._config_dict[DKCloudCommandConfig.DK_CLOUD_DIFF_TOOL] is None:
            raise Exception('Diff tool was not properly configured. Please run \'dk config-list\' to check current\
                configuration and \'dk config\' to change it.')
        return self._config_dict[DKCloudCommandConfig.DK_CLOUD_DIFF_TOOL]

    def get_merge_dir(self, customer_name):
        if not (customer_name and customer_name.strip()):
            raise Exception('Customer name was not properly configured.')
        return os.path.join(self._dk_temp_folder, customer_name, DKCloudCommandConfig.MERGE_DIR)

    def get_diff_dir(self, customer_name):
        if not (customer_name and customer_name.strip()):
            raise Exception('Customer name was not properly configured.')
        return os.path.join(self._dk_temp_folder, customer_name, DKCloudCommandConfig.DIFF_DIR)

    def set_dk_temp_folder(self, dk_temp_folder):
        self._dk_temp_folder = dk_temp_folder

    def init_from_dict(self, set_dict):
        self._config_dict = set_dict
        return self.validate_config()

    def init_from_string(self, jstr):
        try:
            self._config_dict = json.loads(jstr)
        except ValueError, e:
            return False
        return self.validate_config()

    def init_from_file(self, file_json):
        if file_json is None:
            print('DKCloudCommandConfig file path cannot be null')
            rv = False
        else:
            try:
                if file_json[0] == '~':
                    user_home = os.path.expanduser("~")
                    full_path = file_json.replace('~', user_home)
                else:
                    full_path = file_json
                statinfo = os.stat(full_path)
            except Exception:
                pass
                rv = False
            else:
                if statinfo.st_size > 0:
                    with open(full_path) as data_file:
                        try:
                            self._config_dict = json.load(data_file)
                        except ValueError, e:
                            print('DKCloudCommandConfig: failed json.load check syntax %s. %s' % (full_path, e))
                            rv = False
                        else:
                            rv = True
                else:
                    rv = False
        if rv is False:
            return False
        else:
            self.set_file_location(os.path.abspath(full_path))
            return self.validate_config()

    def save_to_stored_file_location(self):
        file_location = self.get_file_location()
        if file_location:
            return self.save_to_file(file_location)
        else:
            return False

    def save_to_file(self, file_location):
        if file_location is None:
            print('DKCloudCommandConfig file path cannot be null')
            return False
        else:
            self.set_file_location(file_location)
            try:
                f = open(file_location, 'w')
                json.dump(self._config_dict, f, sort_keys=True, indent=4)
            except ValueError, e:
                print('DKCloudCommandConfig: failed json.dump %s.' % e)
                return False
            else:
                return True

    def validate_config(self):
        for v in self._required_config_attributes:
            if v not in self._config_dict:
                print("DKCloudCommandConfig: failed to find %s in DKCloudCommandConfig.json" % v)
                return False
        return True
