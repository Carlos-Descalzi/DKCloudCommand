import os
import os.path
import unittest
import time
import ConfigParser
from subprocess import Popen, PIPE
from shutil import copy

CONFIG_FILE_BASE_NAME = 'DKCloudCommandConfig'

config = ConfigParser.ConfigParser()
config.read([os.path.join('.', 'system.test.config')])

DEFAULT_BASE_PATH = config.get('test', 'basepath')
DEFAULT_EMAIL = config.get('test', 'email')
EMAIL_SUFFIX = config.get('test', 'email-suffix')
EMAIL_DOMAIN = config.get('test', 'email-domain')

BASE_PATH = os.environ.get('DK_CLI_SMOKE_TEST_BASE_PATH', DEFAULT_BASE_PATH)
EMAIL = os.environ.get('DK_CLI_SMOKE_TEST_EMAIL', DEFAULT_EMAIL)


class BaseCLISystemTest(unittest.TestCase):
    # ---------------------------- Test setUp and tearDown methods ---------------------------
    def setUp(self):
        pass

    def tearDown(self):
        pass

    # ---------------------------- Helper methods ---------------------------
    def dk_kitchen_config_add(self, kitchen_name, key, value, checks=None, add_params=False):
        if checks is None:
            checks = list()
        checks.append('%s added with value \'%s\'' % (key, value))
        command = 'dk kitchen-config'
        if add_params:
            command += ' --kitchen %s' % kitchen_name
        command += ' --add %s %s' % (key, value)
        sout = self.run_command(command, checks)
        return sout

    def dk_kitchen_delete(self, kitchen_name, checks=None, ignore_checks=False):
        if checks is None:
            checks = list()
        if not ignore_checks:
            checks.append('Kitchen %s has been deleted' % kitchen_name)
        command = 'dk kitchen-delete %s --yes' % kitchen_name
        sout = self.run_command(command, checks, ignore_checks=True)
        return sout

    def dk_kitchen_merge_preview(self, source_kitchen, target_kitchen, checks=None):
        if checks is None:
            checks = list()
        checks.append('- Previewing merge Kitchen %s into Kitchen %s' % (source_kitchen, target_kitchen))
        checks.append('Merge Preview Results (only changed files are being displayed):')
        checks.append('--------------------------------------------------------------')
        checks.append('Kitchen merge preview done.')
        command = 'dk kitchen-merge-preview -cpr --source_kitchen %s --target_kitchen %s' % (source_kitchen, target_kitchen)
        sout = self.run_command(command, checks)
        return sout

    def dk_kitchen_merge(self, source_kitchen, target_kitchen, checks=None):
        if checks is None:
            checks = list()
        checks.append('- Merging Kitchen %s into Kitchen %s' % (source_kitchen, target_kitchen))
        checks.append('Calling Merge ...')
        command = 'dk kitchen-merge --source_kitchen %s --target_kitchen %s --yes' % (source_kitchen, target_kitchen)
        sout = self.run_command(command, checks)
        return sout

    def dk_order_run_info(self, kitchen_name, recipe_name, variation, order_id, checks=None, add_params=False):
        if checks is None:
            checks = list()
        checks.append(' - Display Order-Run details from kitchen %s' % kitchen_name)
        checks.append('ORDER RUN SUMMARY')
        checks.append('Order ID:\t%s' % order_id)
        checks.append('Kitchen:\t%s' % kitchen_name)
        checks.append('Variation:\t%s' % variation)
        checks.append('COMPLETED_SERVING')
        command = 'dk orderrun-info'
        if add_params:
            command += ' --kitchen %s' % kitchen_name
        try:
            self.run_command(command, checks)
        except Exception:
            return False
        return True

    def dk_order_run(self, kitchen_name, recipe_name, variation, checks=None, add_params=False, environment='dk'):
        if checks is None:
            checks = list()
        checks.append(' - Create an Order')
        checks.append('Kitchen: %s' % kitchen_name)
        checks.append('Recipe: %s' % recipe_name)
        checks.append('Variation: %s' % variation)
        checks.append('Order ID is: DKRecipe#%s#%s#%s#%s#' % (environment, recipe_name, variation, kitchen_name))
        kitchen_param_str = ''
        recipe_param_str = ''
        if add_params:
            kitchen_param_str = ' --kitchen %s ' % kitchen_name
            recipe_param_str = '--recipe %s' % recipe_name
        command = 'dk order-run%s%s %s --yes' % (kitchen_param_str, recipe_param_str, variation)
        sout = self.run_command(command, checks)
        aux_string = 'Order ID is: '
        aux_index = sout.find(aux_string)
        order_id = sout[aux_index+len(aux_string):-1].strip()
        return order_id

    def dk_file_update(self, kitchen_name, recipe_name, file_name, message, checks=None):
        if checks is None:
            checks = list()
        checks.append('Updating File(s)')
        checks.append('in Recipe (%s) in Kitchen(%s) with message (%s)' % (recipe_name, kitchen_name, message))
        checks.append('DKCloudCommand.update_file for %s succeeded' % file_name)
        command = 'dk file-update --message "%s" %s' % (message, file_name)
        sout = self.run_command(command, checks)
        return sout

    def dk_recipe_status(self, kitchen_name, recipe_name, qty_of_unchanged_files=None, qty_of_local_changed_files=None, checks=None):
        if checks is None:
            checks = list()

        checks.append('- Getting the status of Recipe \'%s\' in Kitchen \'%s\'' % (recipe_name, kitchen_name))
        if qty_of_unchanged_files is not None:
            checks.append('%d files are unchanged' % qty_of_unchanged_files)
        if qty_of_local_changed_files is not None:
            checks.append('%d files are modified on local' % qty_of_local_changed_files)

        command = 'dk recipe-status'
        sout = self.run_command(command, checks)
        return sout

    def dk_kitchen_which(self, expected_kitchen_name, checks=None):
        if checks is None:
            checks = list()
        checks.append('You are in kitchen \'%s\'' % expected_kitchen_name)
        command = 'dk kitchen-which'
        sout = self.run_command(command, checks)
        return sout

    def dk_recipe_variation_list(self, kitchen_name, recipe_name, checks=None):
        if checks is None:
            checks = list()
        checks.append(' - Listing variations for recipe %s in Kitchen %s' % (recipe_name, kitchen_name))
        checks.append('Variations:')
        command = 'dk recipe-variation-list'
        sout = self.run_command(command, checks)
        return sout

    def dk_recipe_get(self, kitchen_name, recipe_name, checks=None):
        if checks is None:
            checks = list()
        checks.append(' - Getting the latest version of Recipe \'%s\' in Kitchen \'%s\'' % (recipe_name, kitchen_name))
        checks.append('DKCloudCommand.get_recipe has')
        checks.append('sections')
        command = 'dk recipe-get %s' % recipe_name
        sout = self.run_command(command, checks)
        return sout

    def dk_recipe_create(self, kitchen_name, recipe_name, checks=None):
        time.sleep(20)
        if checks is None:
            checks = list()
        checks.append('- Creating Recipe %s for Kitchen \'%s\'' % (recipe_name, kitchen_name))
        checks.append('DKCloudCommand.recipe_create created recipe %s' % recipe_name)
        command = 'dk recipe-create %s' % recipe_name
        sout = self.run_command(command, checks)
        return sout

    def dk_recipe_list(self, kitchen_name, checks=None):
        if checks is None:
            checks = list()
        checks.append('- Getting the list of Recipes for Kitchen \'%s\'' % kitchen_name)
        checks.append('DKCloudCommand.list_recipe returned')
        checks.append('recipes')
        command = 'dk recipe-list'
        sout = self.run_command(command, checks)
        return sout

    def dk_kitchen_get(self, kitchen_name, checks=None):
        if checks is None:
            checks = list()
        checks.append(' - Getting kitchen \'%s\'' % kitchen_name)
        checks.append('Got Kitchen \'%s\'' % kitchen_name)
        command = 'dk kitchen-get %s' % kitchen_name
        sout = self.run_command(command, checks)
        return sout

    def dk_kitchen_create(self, kitchen_name, parent='master', checks=None):
        if checks is None:
            checks = list()
        checks.append(' - Creating kitchen %s from parent kitchen %s' % (kitchen_name, parent))
        checks.append('DKCloudCommand.create_kitchen created %s' % kitchen_name)
        command = 'dk kitchen-create -p %s %s' % (parent, kitchen_name)
        sout = self.run_command(command, checks)
        return sout

    def dk_config_list(self, checks=None):
        if checks is None:
            checks = list()
        checks.append(EMAIL_SUFFIX)
        checks.append('Username')                           #skip-secret-check
        checks.append('Password')                           #skip-secret-check
        checks.append('Cloud IP')
        checks.append('Cloud Port')
        checks.append('Config Location')
        checks.append('General Config Location')
        checks.append('Merge Tool')
        checks.append('Diff Tool')
        sout = self.run_command('dk config-list', checks)
        return sout

    def dk_context_list(self, checks=None):
        if checks is None:
            checks = list()
        checks.append('default')
        checks.append('test')
        checks.append('Current context is: test')
        sout = self.run_command('dk context-list', checks)
        return sout

    def dk_user_info(self, checks=None):
        if checks is None:
            checks = list()
        checks.append('Name:')
        checks.append('Email:')
        checks.append('Customer Name:')
        checks.append('Support Email:')
        checks.append('Role:')

        sout = self.run_command('dk user-info', checks)
        return sout

    def dk_help(self, checks=None):
        if checks is None:
            checks = list()
        checks.append('Usage: dk [OPTIONS] COMMAND [ARGS]...')
        checks.append('config-list (cl)')
        checks.append('user-info (ui)')
        sout = self.run_command('dk --help', checks)
        return sout

    def dk_kitchen_list(self, checks=None):
        if checks is None:
            checks = list()
        checks.append('Getting the list of kitchens')
        checks.append('+---- master')
        sout = self.run_command('dk kl', checks)
        return sout

    def run_command(self, command, checks=None, ignore_checks=False):
        if checks is None:
            checks = list()
        p = Popen(['/bin/sh'], stdout=PIPE, stderr=PIPE, stdin=PIPE)
        sout, serr = p.communicate(command+'\n')
        if not ignore_checks and serr != '':
            message = 'Command %s failed. Standard error is %s' % (command, serr)
            raise Exception(message)
        for s in checks:
            self.assertIn(s, sout)
        return sout

    def set_working_directory(self, path):
        os.chdir(path)
        cwd = os.getcwd()
        self.assertIn(path, cwd)

    # ---------------------------- Start up and Tear down helper methods ---------------------------
    def switch_user_config(self, base_path, configuration):
        if configuration not in ['dk', 'dc']:
            raise Exception('Invalid configuration: %s.\n Should be dk or dc')

        dk_config_base_path = os.path.join(BASE_PATH, '.dk')
        dk_config_source_file_name = '%s-%s.json' % (CONFIG_FILE_BASE_NAME, configuration.upper())
        dk_config_source_file_path = os.path.join(dk_config_base_path, dk_config_source_file_name)

        dk_config_target_file_name = '%s.json' % CONFIG_FILE_BASE_NAME
        dk_config_target_file_path = os.path.join(dk_config_base_path, dk_config_target_file_name)

        copy(dk_config_source_file_path, dk_config_target_file_path)

        time.sleep(5)

    def delete_kitchens_in_tear_down(self, kitchens):
        print '\n----- Delete Kitchens -----'
        for kitchen_name in kitchens:
            if kitchen_name is not None:
                print '-> Deleting kitchen %s' % kitchen_name
                self.dk_kitchen_delete(kitchen_name, ignore_checks=True)

        if len(kitchens) > 0:
            print '-> Checking that kitchens are not in kitchen list any more'
            command_output = self.dk_kitchen_list()
            for kitchen_name in kitchens:
                self.assertTrue(kitchen_name not in command_output)

    def delete_kitchen_path_in_tear_down(self, kitchens_path):
        if kitchens_path is not None:
            print '-> Removing local files from path %s' % kitchens_path
            command = 'rm -rf %s' % kitchens_path
            self.run_command(command)
