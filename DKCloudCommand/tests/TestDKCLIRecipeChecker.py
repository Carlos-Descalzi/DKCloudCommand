import unittest
import os

from DKCloudCommandConfig import DKCloudCommandConfig
from DKCommonUnitTestSettings import DKCommonUnitTestSettings
from DKCLIRecipeChecker import DKCLIRecipeChecker


class TestDKCLIRecipeChecker(DKCommonUnitTestSettings):

    def test_recipe_check_skip(self):
        # config
        skip_recipe_checker = True

        # setup
        cfg = self._create_config(skip_recipe_checker)
        recipe_path = os.path.normpath('./files/recipe_check_bad_001')
        recipe_checker = DKCLIRecipeChecker(cfg)

        # test
        try:
            recipe_checker.check_recipe(recipe_path)
        except Exception as e:
            self.assertTrue(False, 'Recipe Check Failed. Error: %s' % str(e))

    def test_recipe_check_no_recipe(self):
        # setup
        cfg = self._create_config()
        recipe_path = None
        recipe_checker = DKCLIRecipeChecker(cfg)

        # test
        try:
            recipe_checker.check_recipe(recipe_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: None')
        self.assertTrue('- Message: Recipe path is None' in exception_message)

    def test_recipe_check_no_graph(self):
        # setup
        cfg = self._create_config()
        recipe_path = os.path.normpath('./files/recipe_check_bad_001')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker.check_recipe(recipe_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/recipe_check_bad_001/graph.json') in exception_message)
        self.assertTrue('- Message: File is not present in recipe root path' in exception_message)

    def test_recipe_check_good(self):
        # setup
        cfg = self._create_config()
        recipe_path = os.path.normpath('./files/recipe_check_good_001')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker.check_recipe(recipe_path)
        except Exception:
            exception_occurred = True

        # assert
        self.assertFalse(exception_occurred, 'Exception not expected')

    def test_recipe_check_bad_json(self):
        # setup
        cfg = self._create_config()
        recipe_path = os.path.normpath('./files/recipe_check_bad_002_malformed_json')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker.check_recipe(recipe_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/recipe_check_bad_002_malformed_json/resources/email-templates/my.json') in exception_message)
        self.assertTrue('- Message: File has an invalid json format' in exception_message)

    def test_recipe_check_conflicts(self):
        # setup
        cfg = self._create_config()
        recipe_path = os.path.normpath('./files/recipe_check_bad_003_conflicts')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker.check_recipe(recipe_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/recipe_check_bad_003_conflicts/description.json') in exception_message)
        self.assertTrue('- Message: File has merge conflicts.' in exception_message)

    def test_recipe_check_no_description_json(self):
        # setup
        cfg = self._create_config()
        recipe_path = os.path.normpath('./files/recipe_check_bad_no_description_json')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker.check_recipe(recipe_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/recipe_check_bad_no_description_json/placeholder-node2') in exception_message)
        self.assertTrue('- Message: No description.json in node.' in exception_message)

    def test_recipe_check_invalid_node_type(self):
        # setup
        cfg = self._create_config()
        recipe_path = os.path.normpath('./files/recipe_check_bad_description_json_type')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker.check_recipe(recipe_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/recipe_check_bad_description_json_type/load-profits-node') in exception_message)
        self.assertTrue('- Message: Bad node type: "DKNode_Invalid". Needs to be one of this:' in exception_message)

    def test_recipe_check_no_action_folder(self):
        # setup
        cfg = self._create_config()
        recipe_path = os.path.normpath('./files/recipe_check_no_action_folder')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker.check_recipe(recipe_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/recipe_check_no_action_folder/load-profits-node/actions') in exception_message)
        self.assertTrue('- Message: Node has no "actions" folder.' in exception_message)

    def test_recipe_check_invalid_action_type(self):
        # setup
        cfg = self._create_config()
        recipe_path = os.path.normpath('./files/recipe_check_bad_004_invalid_action_type')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker.check_recipe(recipe_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/recipe_check_bad_004_invalid_action_type/pentaho-di-node/actions/DKDataSource_Container.json') in exception_message)
        self.assertTrue('- Message: Bad value "DKDataSource_InvalidType", needs to be one of this list:' in exception_message)

    def test_recipe_bad_action_node_test_action_type(self):
        # setup
        cfg = self._create_config()
        recipe_path = os.path.normpath('./files/recipe_check_bad_action_node_test_action_type')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker.check_recipe(recipe_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/recipe_check_bad_action_node_test_action_type/load-profits-node/actions/load-data.json') in exception_message)
        self.assertTrue('- Message: In "tests", "test-load-data-key", "action". Bad value "warning2", needs to be one of this list:' in exception_message)

    def test_node_noop_good(self):
        # setup
        cfg = self._create_config()
        node_path = os.path.normpath('./files/nodes/noop/noop-good')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker._check_node_DKNode_NoOp(node_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertFalse(exception_occurred, 'Exception not expected')

    def test_node_action_good(self):
        # setup
        cfg = self._create_config()
        node_path = os.path.normpath('./files/nodes/action/action-good')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker._check_node_DKNode_Action(node_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertFalse(exception_occurred, 'Exception not expected')

    def test_node_action_bad_001(self):
        # setup
        cfg = self._create_config()
        node_path = os.path.normpath('./files/nodes/action/action-bad-001')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker._check_node_DKNode_Action(node_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/nodes/action/action-bad-001/actions/load-data.json') in exception_message)
        self.assertTrue('- Message: In "tests", "test-load-data-key", "action". Bad value "warning2", needs to be one of this list:' in exception_message)

    def test_node_container_good(self):
        # setup
        cfg = self._create_config()
        node_path = os.path.normpath('./files/nodes/container/container-good')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker._check_node_DKNode_Container(node_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertFalse(exception_occurred, 'Exception not expected')

    def test_node_container_bad_001(self):
        # setup
        cfg = self._create_config()
        node_path = os.path.normpath('./files/nodes/container/container-bad-001')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker._check_node_DKNode_Container(node_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/nodes/container/container-bad-001/notebook.json') in exception_message)
        self.assertTrue('- Message: File notebook.json is missing' in exception_message)

    def test_node_container_bad_002(self):
        # setup
        cfg = self._create_config()
        node_path = os.path.normpath('./files/nodes/container/container-bad-002')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker._check_node_DKNode_Container(node_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/nodes/container/container-bad-002/notebook.json') in exception_message)
        self.assertTrue('- Message: Mandatory key "image-repo" is missing' in exception_message)

    def test_node_datamapper_good(self):
        # setup
        cfg = self._create_config()
        node_path = os.path.normpath('./files/nodes/datamapper/datamapper-good')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker._check_node_DKNode_DataMapper(node_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertFalse(exception_occurred, 'Exception not expected')

    def test_node_datamapper_bad_001(self):
        # setup
        cfg = self._create_config()
        node_path = os.path.normpath('./files/nodes/datamapper/datamapper-bad-001')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker._check_node_DKNode_DataMapper(node_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/nodes/datamapper/datamapper-bad-001/notebook.json') in exception_message)
        self.assertTrue('- Message: File notebook.json is missing' in exception_message)

    def test_node_datamapper_bad_002(self):
        # setup
        cfg = self._create_config()
        node_path = os.path.normpath('./files/nodes/datamapper/datamapper-bad-002')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker._check_node_DKNode_DataMapper(node_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/nodes/datamapper/datamapper-bad-002/notebook.json') in exception_message)
        self.assertTrue('- Message: Mandatory key "mappings" is missing' in exception_message)

    def test_node_datamapper_bad_003(self):
        # setup
        cfg = self._create_config()
        node_path = os.path.normpath('./files/nodes/datamapper/datamapper-bad-003')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker._check_node_DKNode_DataMapper(node_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/nodes/datamapper/datamapper-bad-003/data_sinks/sink_claims_dx.json') in exception_message)
        self.assertTrue('json file with no "keys"' in exception_message)

    def test_node_ingredient_good(self):
        # setup
        cfg = self._create_config()
        node_path = os.path.normpath('./files/nodes/ingredient/ingredient-good')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker._check_node_DKNode_Ingredient(node_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertFalse(exception_occurred, 'Exception not expected')

    def test_node_ingredient_bad_001(self):
        # setup
        cfg = self._create_config()
        node_path = os.path.normpath('./files/nodes/ingredient/ingredient-bad-001')
        recipe_checker = DKCLIRecipeChecker(cfg)
        exception_occurred = False

        # test
        try:
            recipe_checker._check_node_DKNode_Ingredient(node_path)
        except Exception as e:
            exception_occurred = True
            exception_message = str(e)

        # assert
        self.assertTrue(exception_occurred, 'Exception expected')
        self.assertTrue('---- DKCLIRecipeChecker: ' in exception_message)
        self.assertTrue('- Severity: error' in exception_message)
        self.assertTrue('- File: %s' % os.path.normpath('files/nodes/ingredient/ingredient-bad-001/notebook.json') in exception_message)
        self.assertTrue('- Message: File notebook.json is missing' in exception_message)

    # --------------------------------- Helper Methods -----------------------------------------------------------------
    def _create_config(self, skip_recipe_checker=False):
        cfg = DKCloudCommandConfig()
        config_dict = {
            'dk-cloud-ip': '',
            'dk-cloud-port': '',
            'dk-cloud-username': '',
            'dk-cloud-password': '',
            'dk-cloud-jwt': '',
            'dk-cloud-merge-tool': 'meld {{left}} {{base}} {{right}}',
            'dk-cloud-diff-tool': 'meld {{local}} {{remote}}',
            'dk-skip-recipe-checker': skip_recipe_checker,
            'dk-check-working-path': True
        }
        cfg.init_from_dict(config_dict)
        return cfg


if __name__ == '__main__':
    unittest.main()
