from BaseCLISystemTest import *
from AWSHelper import AWSHelper

config = ConfigParser.ConfigParser()
config.read([os.path.join('.', 'system.test.config')])

AWS_REGION = config.get('test-demo', 'aws-region')
AWS_MSSQL_INSTANCE = config.get('test-demo', 'aws-mssql-instance')
AWS_ACCESS_KEY_ID = config.get('test-demo', 'aws-access-key-id')
AWS_SECRET_ACCESS_KEY = config.get('test-demo', 'aws-secret-access-key')

KITCHEN_PREFIX = 'test_demo'


class TestDemo(BaseCLISystemTest):
    # ---------------------------- Test setUp and tearDown methods ---------------------------
    def setUp(self):
        print '\n\n####################### Setup #######################'
        print 'BASE_PATH: %s' % BASE_PATH
        print 'EMAIL: %s' % EMAIL

        self.kitchens = list()
        self.kitchens_path = BASE_PATH + '/CLISmokeTestDemoKitchens'
        self.aWSHelper = None

    def tearDown(self):
        print '\n####################### Demo has finished #######################'
        print '\n\n####################### TearDown #######################'

        if self.aWSHelper:
            print '-> Stop mssql EC2 instance'
            self.assertTrue(self.aWSHelper.do('stop', [AWS_MSSQL_INSTANCE]))

        print '-> Deleting test kitchens'
        self.delete_kitchens_in_tear_down(self.kitchens)
        print '-> Deleting aux files'
        self.delete_kitchen_path_in_tear_down(self.kitchens_path)

    # ---------------------------- System tests ---------------------------
    def test_demo(self):
        print '\n\n####################### Starting Demo #######################'

        # --------------------------------------------
        print '----> Check logged user'
        configuration = 'dc'
        checks = list()
        checks.append('+%s@%s' % (configuration, EMAIL_DOMAIN))
        sout = self.dk_user_info(checks)

        print 'logged user info: \n%s' % sout

        # --------------------------------------------
        print '-> Make sure CLI is working'
        self.dk_help()

        # --------------------------------------------
        print '-> Start mssql EC2 instance'
        if all([AWS_REGION, AWS_MSSQL_INSTANCE, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY]):
            self.aWSHelper = AWSHelper(AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
            self.assertTrue(self.aWSHelper.do('start', [AWS_MSSQL_INSTANCE]))
        else:
            self.assertTrue(False, 'EC2 instance, region and access not properly configured')

        # --------------------------------------------
        print '-> Cleanup previous kitchens'

        kitchen_name_prod = '%s_warehouse_Production_Sales' % KITCHEN_PREFIX
        kitchen_name_dev = '%s_warehouse_Development_Sales' % KITCHEN_PREFIX

        self.kitchens.append(kitchen_name_prod)
        self.kitchens.append(kitchen_name_dev)

        for kitchen_name in self.kitchens:
            if kitchen_name is not None:
                print '-> Deleting kitchen %s' % kitchen_name
                self.dk_kitchen_delete(kitchen_name, ignore_checks=True)

        # --------------------------------------------
        recipe_name = 'warehouse'
        variation = '0-Demo-Setup'
        kitchen_name = 'master'
        print '-> Run order for %s/%s in kitchen %s' % (recipe_name, variation, kitchen_name)
        order_id = self.dk_order_run(kitchen_name, recipe_name, variation, add_params=True, environment=configuration)
        print 'Order id = %s' % order_id
        retry_qty = 5
        order_run_completed = False
        seconds = 60
        while not order_run_completed and retry_qty > 0:
            retry_qty = retry_qty - 1
            print '-> Waiting for %d seconds ' % seconds
            time.sleep(seconds)

            print '-> Pull order run status for %s' % order_id
            order_run_completed = self.dk_order_run_info(kitchen_name, recipe_name, variation, order_id, add_params=True)

        self.assertTrue(order_run_completed, msg='Order run has not shown as completed after multiple status fetch')

        print '-> Create %s kitchen' % kitchen_name_prod
        self.dk_kitchen_create(kitchen_name_prod, parent='master')

        print '-> Create %s kitchen' % kitchen_name_dev
        self.dk_kitchen_create(kitchen_name_dev, parent=kitchen_name_prod)

        print '-> Add config sql_database_kitchen = sales_dev to kitchen %s' % kitchen_name_dev
        self.dk_kitchen_config_add(kitchen_name_dev, 'sql_database_kitchen', 'sales_dev', add_params=True)

        # --------------------------------------------
        recipe_name = 'warehouse'
        variation = 'Production-Update-scheduled'
        kitchen_name = kitchen_name_prod
        print '-> Run order for %s/%s in kitchen %s' % (recipe_name, variation, kitchen_name)
        order_id = self.dk_order_run(kitchen_name, recipe_name, variation, add_params=True, environment=configuration)
        print 'Order id = %s' % order_id

        retry_qty = 5
        order_run_completed = False
        seconds = 80
        while not order_run_completed and retry_qty > 0:
            retry_qty = retry_qty - 1
            print '-> Waiting for %d seconds ' % seconds
            time.sleep(seconds)

            print '-> Pull order run status for %s ' % order_id
            order_run_completed = self.dk_order_run_info(kitchen_name, recipe_name, variation, order_id, add_params=True)

        self.assertTrue(order_run_completed, msg='Order run has not shown as completed after multiple status fetch')

        # --------------------------------------------
        recipe_name = 'warehouse'
        variation = 'Synch-Prod-To-Dev'
        kitchen_name = kitchen_name_prod
        print '-> Run order for %s/%s in kitchen %s' % (recipe_name, variation, kitchen_name)
        order_id = self.dk_order_run(kitchen_name, recipe_name, variation, add_params=True, environment=configuration)
        print 'Order id = %s' % order_id
        retry_qty = 5
        order_run_completed = False
        seconds = 60
        while not order_run_completed and retry_qty > 0:
            retry_qty = retry_qty - 1
            print '-> Waiting for %d seconds ' % seconds
            time.sleep(seconds)

            print '-> Pull order run status for %s' % order_id
            order_run_completed = self.dk_order_run_info(kitchen_name, recipe_name, variation, order_id, add_params=True)

        self.assertTrue(order_run_completed, msg='Order run has not shown as completed after multiple status fetch')


if __name__ == '__main__':
    print 'Running CLI smoke tests - Demo'
    print 'To configure, set this environment variables, otherwise will use default values:'
    print '\tDK_CLI_SMOKE_TEST_BASE_PATH: %s' % BASE_PATH
    print '\tDK_CLI_SMOKE_TEST_EMAIL: %s\n' % EMAIL
    unittest.main()
