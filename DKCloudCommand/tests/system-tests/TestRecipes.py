import os
import unittest
import time
from DKFileUtils import DKFileUtils
from BaseCLISystemTest import *
from shutil import copy

CONFIG_FILE_BASE_NAME = 'DKCloudCommandConfig'
MAX_ORDER_RUN_STATUS_RETRY_QTY = 30
ORDER_RUN_STATUS_RETRY_DELAY = 30

RECIPE_LIST = [
    {
        'configuration': 'dk',
        'parent_kitchen': 'master',
        'recipe': 'parallel-recipe-test',
        'variation': 'variation-test'
    }
]

'''
,
{
    'configuration': 'dc',
    'parent_kitchen': 'master',
    'recipe': 'parallel-recipe-test',
    'variation': 'variation-test'
}
'''


class TestRecipes(BaseCLISystemTest):
    # ---------------------------- Test setUp and tearDown methods ---------------------------
    def setUp(self):
        print '\n\n####################### Setup #######################'
        self.test_id = 'cli-system-test-recipe'
        self.kitchens_path = BASE_PATH + '/CLITestRecipesKitchens'
        print 'BASE_PATH: %s' % BASE_PATH
        print 'EMAIL: %s' % EMAIL
        pass

    def tearDown(self):
        self.delete_kitchen_path_in_tear_down(self.kitchens_path)
        pass

    # ---------------------------- System tests ---------------------------
    def test_recipes(self):
        print '\n\n####################### Test Recipes #######################'

        for recipe_item in RECIPE_LIST:

            # --------------------------------------------
            print '----> Recipe Setup'
            configuration = recipe_item['configuration']
            parent_kitchen = recipe_item['parent_kitchen']
            recipe = recipe_item['recipe']
            variation = recipe_item['variation']

            if any([configuration, parent_kitchen, recipe, variation]) is None:
                self.assertTrue(False, 'Invalid configuration: None')

            if configuration not in ['dk', 'dc']:
                self.assertTrue(False, 'Invalid configuration in recipe: %s' % configuration)

            # --------------------------------------------
            print '----> Proceeding with recipe:'
            print '\tconfiguration   > %s' % configuration
            print '\tparent_kitchen  > %s' % parent_kitchen
            print '\trecipe          > %s' % recipe
            print '\tvariation       > %s' % variation
            print '\n'

            # --------------------------------------------
            print '----> Switch user config'                        #skip-secret-check
            dk_config_base_path = os.path.join(BASE_PATH, '.dk')
            dk_config_source_file_name = '%s-%s.json' % (CONFIG_FILE_BASE_NAME, configuration.upper())
            dk_config_source_file_path = os.path.join(dk_config_base_path, dk_config_source_file_name)

            dk_config_target_file_name = '%s.json' % CONFIG_FILE_BASE_NAME
            dk_config_target_file_path = os.path.join(dk_config_base_path, dk_config_target_file_name)

            copy(dk_config_source_file_path, dk_config_target_file_path)

            time.sleep(5)

            # --------------------------------------------
            print '----> Check logged user'                         #skip-secret-check
            checks = list()
            checks.append('+%s%s' % (configuration, EMAIL_DOMAIN))
            sout = self.dk_user_info(checks)

            print 'logged user info: \n%s' % sout                   #skip-secret-check

            # --------------------------------------------
            print '-> Local path prep'
            DKFileUtils.create_dir_if_not_exists(self.kitchens_path)
            self.set_working_directory(self.kitchens_path)

            # --------------------------------------------
            print '----> Create new kitchen for test'
            current_kitchen = '%s-%s-%s-%s-%s' % (self.test_id, configuration, parent_kitchen, recipe, variation)
            self.dk_kitchen_delete(current_kitchen)
            time.sleep(10)
            self.dk_kitchen_create(current_kitchen, parent=parent_kitchen)

            print '-> List kitchens and check the new ones'
            checks = list()
            checks.append(current_kitchen)
            self.dk_kitchen_list(checks)

            # --------------------------------------------
            print '-> Get kitchen to local'
            self.dk_kitchen_get(current_kitchen)
            kitchen_local_dir = '%s/%s' % (self.kitchens_path, current_kitchen)
            self.assertTrue(os.path.exists(kitchen_local_dir))

            print '\n----- List Recipes -----'

            print '-> Set local working directory as: %s' % kitchen_local_dir
            self.set_working_directory(kitchen_local_dir)

            print '-> Perform a recipe list'
            checks = list()
            checks.append(recipe)
            self.dk_recipe_list(current_kitchen, checks)

            print '\n----- Get Local Recipe Copy -----'
            print '-> Get the recipe %s' % recipe
            expected_paths = list()
            expected_paths.append('%s/description.json' % recipe)
            expected_paths.append('%s/graph.json' % recipe)
            expected_paths.append('%s/variations.json' % recipe)
            expected_paths.append('%s/variables.json' % recipe)

            checks = list()
            self.dk_recipe_get(current_kitchen, recipe, checks=checks)
            for path in expected_paths:
                self.assertTrue(os.path.exists('%s/%s' % (kitchen_local_dir, path)))

            print '\n----- View Recipe Variations -----'

            recipe_local_dir = '%s/%s' % (kitchen_local_dir, recipe)
            print '-> Set local working directory as: %s' % recipe_local_dir
            self.assertTrue(os.path.exists(recipe_local_dir))
            self.set_working_directory(recipe_local_dir)

            print '-> Get recipe variation list'
            checks = list()
            checks.append(variation)
            self.dk_recipe_variation_list(current_kitchen, recipe, checks)

            print '\n----- Run an Order -----'
            print '-> Running the order'
            order_id = self.dk_order_run(current_kitchen, recipe, variation)

            print '\n----- View Order-Run Details -----'

            print '-> Pulling order run status: Start'
            retry_qty = MAX_ORDER_RUN_STATUS_RETRY_QTY
            order_run_completed = False
            seconds = ORDER_RUN_STATUS_RETRY_DELAY
            while not order_run_completed and retry_qty > 0:
                retry_qty = retry_qty - 1
                print '-> Waiting %d seconds ' % seconds
                time.sleep(seconds)

                print '-> Pull order run status'
                order_run_completed = self.dk_order_run_info(current_kitchen, recipe, variation, order_id)

            self.assertTrue(order_run_completed, msg='Order run has not shown as completed after multiple status fetch')
            print '-> Pulling order run status: Done'

            self.set_working_directory(BASE_PATH)
            print '-> Deleting kitchen %s' % current_kitchen
            self.dk_kitchen_delete(current_kitchen)

            print '----> Recipe Done!'


if __name__ == '__main__':
    print 'Running CLI smoke tests - Test Recipes'
    print 'To configure, set this environment variables, otherwise will use default values:'
    print '\tDK_CLI_SMOKE_TEST_BASE_PATH: Default is /home/vagrant'
    print '\tDK_CLI_SMOKE_TEST_EMAIL: Default is %s\n' % EMAIL
    unittest.main()
