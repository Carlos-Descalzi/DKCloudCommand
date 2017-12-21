import os
import unittest
import time
import random
from DKFileUtils import DKFileUtils
from BaseCLISystemTest import *


class TestQuickStart(BaseCLISystemTest):
    # ---------------------------- Test setUp and tearDown methods ---------------------------
    def setUp(self):
        print '\n\n####################### Setup #######################'
        print 'BASE_PATH: %s' % BASE_PATH
        print 'EMAIL: %s' % EMAIL

        self.kitchens = list()
        self.kitchens_path = BASE_PATH + '/CLISmokeTestKitchens'

    def tearDown(self):
        print '\n####################### Quick Start 1 has finished #######################'
        print '\n\n####################### TearDown #######################'

        self.delete_kitchens_in_tear_down(self.kitchens)
        self.delete_kitchen_path_in_tear_down(self.kitchens_path)

    # ---------------------------- System tests ---------------------------
    def test_quick_start_1(self):
        print '\n\n####################### Starting Quick Start 1 #######################'
        print '\n---- Pre-Heat the Oven ----'

        print '-> Make sure CLI is working'
        self.dk_help()

        print '-> Local path prep'
        test_id = 'cli-smoke-test-1-%05d-' % random.randint(0, 10000)
        kitchens_path = self.kitchens_path
        DKFileUtils.create_dir_if_not_exists(kitchens_path)
        self.set_working_directory(kitchens_path)

        print '-> Make sure CLI is pointing at dk repo (a +dk email configured)'
        self.dk_config_list()

        print '\n----- The Master Kitchen -----'

        print '-> List current kitchens'
        self.dk_kitchen_list()

        print '-> Create new kitchen master for unit test'
        self.master_kitchen = '%sMaster' % test_id
        self.kitchens.append(self.master_kitchen)
        self.dk_kitchen_create(self.master_kitchen, parent='master')

        print '-> Create new kitchen unit test Production'
        self.production_kitchen = '%sProduction' % test_id
        self.kitchens.append(self.production_kitchen)
        self.dk_kitchen_create(self.production_kitchen, parent=self.master_kitchen)

        print '-> Create new kitchen unit test Dev-Sprint-1'
        self.dev_sprint_1_kitchen = '%sDev-Sprint-1' % test_id
        self.kitchens.append(self.dev_sprint_1_kitchen)
        self.dk_kitchen_create(self.dev_sprint_1_kitchen, parent=self.production_kitchen)

        print '-> Create new kitchen unit test Feature_Sprint_1'
        self.feature_sprint_1_kitchen = '%sFeature-Sprint-1' % test_id
        self.kitchens.append(self.feature_sprint_1_kitchen)
        self.dk_kitchen_create(self.feature_sprint_1_kitchen, parent=self.dev_sprint_1_kitchen)

        print '-> List kitchens and check the new ones'
        checks = list()
        checks.append(self.master_kitchen)
        checks.append(self.production_kitchen)
        checks.append(self.dev_sprint_1_kitchen)
        checks.append(self.feature_sprint_1_kitchen)
        self.dk_kitchen_list(checks)

        print '\n----- Get Kitchen to Local -----'

        print '-> Get kitchen to local: Feature_Sprint_1'
        self.dk_kitchen_get(self.feature_sprint_1_kitchen)
        feature_sprint_1_kitchen_local_dir = '%s/%s' % (kitchens_path, self.feature_sprint_1_kitchen)
        self.assertTrue(os.path.exists(feature_sprint_1_kitchen_local_dir))

        print '\n----- List Recipes -----'

        print '-> Set local working directory as: %s' % feature_sprint_1_kitchen_local_dir
        self.set_working_directory(feature_sprint_1_kitchen_local_dir)

        print '-> Perform a recipe list'
        self.dk_recipe_list(self.feature_sprint_1_kitchen)

        print '\n----- Create a Recipe -----'
        recipe_name = 'CLI-QS1-Recipe-Template'
        print '-> Creating the recipe \'%s\'' % recipe_name
        self.dk_recipe_create(self.feature_sprint_1_kitchen, recipe_name)

        print '-> Performing a recipe list checking %s' % recipe_name
        self.dk_recipe_list(self.feature_sprint_1_kitchen, checks=[recipe_name])

        print '\n----- Get Local Recipe Copy -----'

        print '-> Get the recipe %s' % recipe_name
        expected_paths = list()
        expected_paths.append('%s/resources' % recipe_name)
        expected_paths.append('%s/resources/email-templates' % recipe_name)
        expected_paths.append('%s/placeholder-node1' % recipe_name)
        expected_paths.append('%s/placeholder-node2' % recipe_name)

        checks = list()
        checks.extend(expected_paths)
        self.dk_recipe_get(self.feature_sprint_1_kitchen, recipe_name, checks=checks)

        for path in expected_paths:
            self.assertTrue(os.path.exists('%s/%s' % (feature_sprint_1_kitchen_local_dir, path)))

        print '\n----- View Recipe Variations -----'

        recipe_template_local_dir = '%s/%s/%s' % (kitchens_path, self.feature_sprint_1_kitchen, recipe_name)
        print '-> Set local working directory as: %s' % recipe_template_local_dir
        self.assertTrue(os.path.exists(recipe_template_local_dir))
        self.set_working_directory(recipe_template_local_dir)

        print '-> Get recipe variation list'
        checks = list()
        checks.append('Variation1')
        self.dk_recipe_variation_list(self.feature_sprint_1_kitchen, recipe_name, checks)

        print '\n----- Recipe Structure -----'

        print '-> Listing recipe structure'
        checks = list()

        checks.append('description.json')
        checks.append('graph.json')
        checks.append('variables.json')
        checks.append('variations.json')
        checks.append('placeholder-node1')
        checks.append('placeholder-node2')
        checks.append('description.json')
        checks.append('resources')
        checks.append('email-templates')
        checks.append('README.txt')
        checks.append('resources/email-templates')
        checks.append('dk_recipe_done_email_template.html')
        checks.append('dk_recipe_over_duration_email_template.html')
        checks.append('dk_recipe_startup_email_template.html')

        command = 'ls -R *'
        self.run_command(command, checks)

        print '\n----- Which Kitchen? -----'

        print '-> Executing which kitchen command'
        self.dk_kitchen_which(self.feature_sprint_1_kitchen)

        print '\n----- Recipe Status -----'

        print '-> Executing recipe status command'
        self.dk_recipe_status(self.feature_sprint_1_kitchen, recipe_name, qty_of_unchanged_files=10)

        print '\n----- Local Recipe Change -----'

        print '-> Changing variables.json with email'
        variables_json_full_path = '%s/variables.json' % recipe_template_local_dir
        file_contents = DKFileUtils.read_file(variables_json_full_path)
        file_contents = file_contents.replace('[YOUR EMAIL HERE]', EMAIL)
        DKFileUtils.write_file(variables_json_full_path, file_contents)

        print '-> Executing recipe status command to verify changes'
        checks = list()
        checks.append('variables.json')
        self.dk_recipe_status(self.feature_sprint_1_kitchen, recipe_name,
                              qty_of_local_changed_files=1,
                              qty_of_unchanged_files=9,
                              checks=checks)

        print '\n----- Update: Local to Remote -----'
        print '-> Executing file-update for variables.json'
        self.dk_file_update(self.feature_sprint_1_kitchen, recipe_name,
                            'variables.json',
                            'CLI Smoke Test Quick Start 1 - Push email value update within variables.json')

        print '-> Executing recipe-status to make sure there are no more local changes'
        self.dk_recipe_status(self.feature_sprint_1_kitchen, recipe_name, qty_of_unchanged_files=10)

        print '\n----- Run an Order -----'
        print '-> Running the order'
        order_id = self.dk_order_run(self.feature_sprint_1_kitchen, recipe_name, 'Variation1')

        print '\n----- View Order-Run Details -----'

        print '-> Pulling order run status: Start'
        retry_qty = 20
        order_run_completed = False
        seconds = 20
        while not order_run_completed and retry_qty > 0:
            retry_qty = retry_qty - 1
            print '-> Waiting %d seconds ' % seconds
            time.sleep(seconds)

            print '-> Pull order run status'
            order_run_completed = self.dk_order_run_info(self.feature_sprint_1_kitchen, recipe_name, 'Variation1', order_id)

        self.assertTrue(order_run_completed, msg='Order run has not shown as completed after multiple status fetch')
        print '-> Pulling order run status: Done'

        print '\n----- Merge Parent to Child -----'

        print '-> Reverse merge: Dev_Sprint_1 to Feature_Sprint_1 - Preview'
        self.set_working_directory(kitchens_path)
        source_kitchen = self.dev_sprint_1_kitchen
        target_kitchen = self.feature_sprint_1_kitchen

        checks = list()
        checks.append('Nothing to merge.')
        self.dk_kitchen_merge_preview(source_kitchen, target_kitchen, checks=checks)

        print '-> Reverse merge: Dev_Sprint_1 to Feature_Sprint_1 - Actual Merge'
        checks = list()
        checks.append('base already contains the head, nothing to merge')
        self.dk_kitchen_merge(source_kitchen, target_kitchen, checks=checks)

        print '\n----- Merge Child to Parent -----'

        print '-> Before the merge, make sure recipe is not already present in parent kitchen Dev_Sprint_1'
        self.set_working_directory(kitchens_path)
        self.dk_kitchen_get(self.dev_sprint_1_kitchen)
        dev_sprint_1_kitchen_local_dir = '%s/%s' % (kitchens_path, self.dev_sprint_1_kitchen)
        self.assertTrue(os.path.exists(dev_sprint_1_kitchen_local_dir))
        self.set_working_directory(dev_sprint_1_kitchen_local_dir)

        command_output = self.dk_recipe_list(self.dev_sprint_1_kitchen)
        self.assertTrue(recipe_name not in command_output)

        print '-> Switching back to Feature_Sprint_1 path'
        recipe_template_local_dir = '%s/%s/%s' % (kitchens_path, self.feature_sprint_1_kitchen, recipe_name)
        print '-> Set local working directory as: %s' % recipe_template_local_dir
        self.assertTrue(os.path.exists(recipe_template_local_dir))
        self.set_working_directory(recipe_template_local_dir)

        print '-> Merge: Feature_Sprint_1 to Dev_Sprint_1 - Preview'
        source_kitchen = self.feature_sprint_1_kitchen
        target_kitchen = self.dev_sprint_1_kitchen

        checks = list()
        checks.append('      ok		%s/resources/email-templates/dk_recipe_over_duration_email_template.html' % recipe_name)
        checks.append('      ok		%s/resources/email-templates/dk_recipe_startup_email_template.html' % recipe_name)
        checks.append('      ok		%s/resources/email-templates/dk_recipe_done_email_template.html' % recipe_name)
        checks.append('      ok		%s/resources/README.txt' % recipe_name)
        checks.append('      ok		%s/placeholder-node1/description.json' % recipe_name)
        checks.append('      ok		%s/variations.json' % recipe_name)
        checks.append('      ok		%s/description.json' % recipe_name)
        checks.append('      ok		%s/placeholder-node2/description.json' % recipe_name)
        checks.append('      ok		%s/graph.json' % recipe_name)
        checks.append('      ok		%s/variables.json' % recipe_name)
        self.dk_kitchen_merge_preview(source_kitchen, target_kitchen, checks=checks)

        print '-> Merge: Feature_Sprint_1 to Dev_Sprint_1 - Actual Merge'
        checks = list()
        checks.append('description.json')
        checks.append('graph.json')
        checks.append('variables.json')
        checks.append('variations.json')
        checks.append('README.txt')
        checks.append('dk_recipe_done_email_template.html')
        checks.append('dk_recipe_over_duration_email_template.html')
        checks.append('dk_recipe_startup_email_template.html')
        checks.append('10 files changed')

        self.dk_kitchen_merge(source_kitchen, target_kitchen, checks=checks)

        print '-> Checking recipe list in parent kitchen (Dev_Sprint_1) contains new recipe'
        dev_sprint_1_kitchen_local_dir = '%s/%s' % (kitchens_path, self.dev_sprint_1_kitchen)
        self.set_working_directory(dev_sprint_1_kitchen_local_dir)

        checks = list()
        checks.append(recipe_name)
        self.dk_recipe_list(self.dev_sprint_1_kitchen, checks=checks)


if __name__ == '__main__':
    print 'Running CLI smoke tests - Quick Start'
    print 'To configure, set this environment variables, otherwise will use default values:'
    print '\tDK_CLI_SMOKE_TEST_BASE_PATH: Default is /home/vagrant'
    print '\tDK_CLI_SMOKE_TEST_EMAIL: Default is %s\n' % EMAIL
    unittest.main()
