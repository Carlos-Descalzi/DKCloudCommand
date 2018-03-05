#!/usr/bin/env python

import click
import os, stat
from sys import path, exit
import sys
from os.path import expanduser
from signal import signal, SIGINT, getsignal
from datetime import datetime
import getpass
import json
import requests

__author__ = 'DataKitchen, Inc.'

home = expanduser('~')  # does not end in a '/'
if os.path.join(home, 'dev/DKCloudCommand') not in path:
    path.insert(0, os.path.join(home, 'dev/DKCloudCommand'))
from DKCloudCommand.modules.DKCloudAPI import DKCloudAPI
from DKCloudCommand.modules.DKCloudCommandConfig import DKCloudCommandConfig
from DKCloudCommand.modules.DKCloudCommandRunner import DKCloudCommandRunner
from DKCloudCommand.modules.DKKitchenDisk import DKKitchenDisk
from DKCloudCommand.modules.DKRecipeDisk import DKRecipeDisk

DEFAULT_IP = 'https://cloud.datakitchen.io'
DEFAULT_PORT = '443'

DK_VERSION = '1.0.61'

alias_exceptions = {'recipe-conflicts': 'rf',
                    'kitchen-config': 'kf',
                    'recipe-create': 're',
                    'file-diff': 'fdi'}


class Backend(object):
    _short_commands = {}

    def __init__(self, config_path_param=None):
        dk_temp_folder = os.path.join(home,'.dk')
        if config_path_param is None:
            if os.environ.get('DKCLI_CONFIG_LOCATION') is not None:
                self.config_file_location = os.path.expandvars('${DKCLI_CONFIG_LOCATION}').strip()
            else:
                try:
                    os.makedirs(dk_temp_folder)
                except: 
                    pass
                self.config_file_location = os.path.join(dk_temp_folder,"DKCloudCommandConfig.json")
        else:
            self.config_file_location = config_path_param

        if not self.check_version():
            exit(1)

        if not os.path.isfile(self.config_file_location):
            self.setup_cli(self.config_file_location)

        cfg = DKCloudCommandConfig()
        cfg.set_dk_temp_folder(dk_temp_folder)
        if not cfg.init_from_file(self.config_file_location):
            s = "Unable to load configuration from '%s'" % self.config_file_location
            raise click.ClickException(s)
        self.dki = DKCloudAPI(cfg)
        if self.dki is None:
            s = 'Unable to create and/or connect to backend object.'
            raise click.ClickException(s)
        token = self.dki.login()
        if token is None:
            s = 'login failed'
            raise click.ClickException(s)


    def check_version(self):
        if 'DKCLI_SKIP_VERSION_CHECK' in os.environ:
            return True
        
        current_version = self.version_to_int(DK_VERSION)

        folder,_ = os.path.split(self.config_file_location)

        latest_version_file = os.path.join(folder,'.latest_version')

        latest_version = None

        if os.path.exists(latest_version_file):
            with open(latest_version_file,'r') as f:
                latest_version = f.read().strip()

        if not latest_version or self.version_to_int(latest_version) <= current_version:
            try:
                response = requests.get('http://pypi.python.org/pypi/DKCloudCommand/json')

                info_json = response.json()

                latest_version = info_json['info']['version']

                with open(latest_version_file,'w') as f:
                    f.write(latest_version)
            except:
                pass

        if latest_version and self.version_to_int(latest_version) > current_version:

            print '\033[31m***********************************************************************************\033[39m'
            print '\033[31m Warning !!!\033[39m'
            print '\033[31m Your command line is out of date, new version %s is available. Please update.\033[39m' % latest_version
            print ''
            print '\033[31m Type "pip install DKCloudCommand --upgrade" to upgrade.\033[39m'
            print '\033[31m***********************************************************************************\033[39m'
            print ''

            return False

        return True

    def version_to_int(self,version_str):
        tokens = version_str.split('.')
        tokens.reverse()
        return sum([int(v) * pow(100,i) for i,v in enumerate(tokens)])

    def setup_cli(self,file_path,full=False):

        print ''

        username = raw_input('Enter username:')
        password = getpass.getpass('Enter password:')

        ip = ''
        port = ''
        merge_tool = ''
        diff_tool = ''

        if full:
            ip = raw_input('DK Cloud Address (default https://cloud.datakitchen.io):')
            port = raw_input('DK Cloud Port (default 443):')
            merge_tool = raw_input('DK Cloud Merge Tool Template (default None):')
            diff_tool = raw_input('DK Cloud File Diff Tool Template (default None):')

        if not ip:
            ip = DEFAULT_IP
        if not port:
            port = DEFAULT_PORT

        print ''
        if username == '' or password == '':
            raise click.ClickException("Invalid credentials")

        #Use production settings.
        data = {
            'dk-cloud-file-location': file_path,
            'dk-cloud-ip': ip,
            'dk-cloud-port': port,
            'dk-cloud-username': username,
            'dk-cloud-password': password,
            'dk-cloud-diff-tool': diff_tool,
            'dk-cloud-merge-tool': merge_tool
        }
        with open(file_path,'w') as f:
            json.dump(data,f,indent=4)


    @staticmethod
    def get_kitchen_name_soft(given_kitchen=None):
        """
        Get the kitchen name if it is available.
        :return: kitchen name or None
        """
        if given_kitchen is not None:
            return given_kitchen
        else:
            in_kitchen = DKCloudCommandRunner.which_kitchen_name()
            return in_kitchen

    @staticmethod
    def check_in_kitchen_root_folder_and_get_name():
        """
        Ensures that the caller is in a kitchen folder.
        :return: kitchen name or None
        """
        in_kitchen = DKCloudCommandRunner.which_kitchen_name()
        if in_kitchen is None:
            raise click.ClickException("Please change directory to a kitchen folder.")
        else:
            return in_kitchen

    @staticmethod
    def get_kitchen_from_user(kitchen=None):
        in_kitchen = DKCloudCommandRunner.which_kitchen_name()
        if kitchen is None and in_kitchen is None:
            raise click.ClickException("You must provide a kitchen name or be in a kitchen folder.")

        if in_kitchen is not None:
            use_kitchen = in_kitchen

        if kitchen is not None:
            use_kitchen = kitchen

        use_kitchen = Backend.remove_slashes(use_kitchen)

        return "ok", use_kitchen

    @staticmethod
    def get_recipe_name(recipe):
        in_recipe = DKRecipeDisk.find_recipe_name()
        if recipe is None and in_recipe is None:
            raise click.ClickException("You must provide a recipe name or be in a recipe folder.")
        elif recipe is not None and in_recipe is not None:
            raise click.ClickException(
                    "Please provide a recipe parameter or change directory to a recipe folder, not both.\nYou are in Recipe '%s'" % in_recipe)

        if in_recipe is not None:
            use_recipe = in_recipe
        else:
            use_recipe = recipe

        use_recipe = Backend.remove_slashes(use_recipe)
        return "ok", use_recipe

    @staticmethod
    def remove_slashes(name):
        if len(name) > 1 and (name.endswith('\\') or name.endswith('/')):
            return name[:-1]
        return name

    def set_short_commands(self, commands):
        short_commands = {}
        for long_command in commands:
            if long_command in alias_exceptions:
                short_commands[long_command] = alias_exceptions[long_command]
                continue
            parts = long_command.split('-')
            short_command = ''
            for part in parts:
                if part == 'orderrun':
                    short_command += 'or'
                else:
                    short_command += part[0]
            short_commands[long_command] = short_command
        self._short_commands = short_commands
        return self._short_commands

    def get_short_commands(self):
        return self._short_commands


def check_and_print(rc):
    if rc.ok():
        click.echo(rc.get_message())
    else:
        raise click.ClickException(rc.get_message())


class AliasedGroup(click.Group):

    # def format_commands(self, ctx, formatter):
    #     #super(AliasedGroup, self).format_commands(ctx, formatter)
    #     """Extra format methods for multi methods that adds all the commands
    #     after the options.
    #     """
    #     rows = []
    #     for subcommand in self.list_commands(ctx):
    #         cmd = self.get_command(ctx, subcommand)
    #         # What is this, the tool lied about a command.  Ignore it
    #         if cmd is None:
    #             continue
    #
    #         help = cmd.short_help or ''
    #         rows.append((subcommand, help))
    #
    #     if rows:
    #         with formatter.section('Commands'):
    #             formatter.write_dl(rows)
    #
    #         with formatter.section('ShortCommands'):
    #             formatter.write_dl(rows)

    def get_command(self, ctx, cmd_name):
        self._check_unique(ctx)
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        found_command = next(
            (long_command for long_command, short_command in alias_exceptions.items() if short_command == cmd_name),
            None)

        if found_command is not None:
            return click.Group.get_command(self, ctx, found_command)

        all_commands = self.list_commands(ctx)
        for long_command in all_commands:
            short_command = self.short_command(long_command)
            if short_command == cmd_name:
                return click.Group.get_command(self, ctx, long_command)
        ctx.fail("Unable to find command for alias '%s'" % cmd_name)

    def short_command(self,long_command):
        if long_command in alias_exceptions:
            return alias_exceptions[long_command]
        parts = long_command.split('-')
        short_command = ''
        for part in parts:
            if part == 'orderrun':
                short_command += 'or'
            else:
                short_command += part[0]
        return short_command

    def _check_unique(self, ctx):
        all_commands = self.list_commands(ctx)
        short_commands = {}
        for long_command in all_commands:
            if long_command in alias_exceptions:
                continue

            short_command = self.short_command(long_command)

            if short_command in short_commands:
                click.secho("The short alias %s is not ambiguous" % short_command, fg='red')
            else:
                short_commands[short_command] = long_command

    def format_commands(self, ctx, formatter):
        # override default behavior
        rows = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue

            help = cmd.short_help or ''
            rows.append(('%s (%s)' % (subcommand, self.short_command(subcommand)), help))

        if rows:
            with formatter.section('Commands'):
                formatter.write_dl(rows)


@click.group(cls=AliasedGroup)
@click.option('--config', '-c', type=str, required=False, help='Path to config file')
@click.version_option(version=DK_VERSION)
@click.pass_context
def dk(ctx, config):
    ctx.obj = Backend(config)
    ctx.obj.set_short_commands(ctx.command.commands)
    # token = ctx.obj.dki._auth_token
    # if token is None:
    #     exit(1)


# Use this to override the automated help
class DKClickCommand(click.Command):
    def __init__(self, name, context_settings=None, callback=None,
                 params=None, help=None, epilog=None, short_help=None,
                 options_metavar='[OPTIONS]', add_help_option=True):
        super(DKClickCommand, self).__init__(name, context_settings, callback,
                                             params, help, epilog, short_help,
                                             options_metavar, add_help_option)

    def get_help(self, ctx):
        # my_help = click.Command.get_help(ctx)
        my_help = super(DKClickCommand, self).get_help(ctx)
        return my_help


@dk.command(name='config-list', cls=DKClickCommand)
@click.pass_obj
def config_list(backend):
    """
    Print the current configuration.
    """
    click.secho('Current configuration is ...', fg='green')

    ret = str()
    customer_name = backend.dki.get_customer_name()
    if customer_name:
        ret += 'Customer Name:\t\t%s\n' % str(customer_name)
    ret += str(backend.dki.get_config())
    print ret


@dk.command(name='config',cls=DKClickCommand)
@click.pass_obj
def config(backend):
    """
    Configure Command Line.
    """
    backend.setup_cli(backend.config_file_location,True)


@dk.command(name='recipe-status')
@click.pass_obj
def recipe_status(backend):
    """
    Compare local recipe to remote recipe for the current recipe.
    """
    kitchen = DKCloudCommandRunner.which_kitchen_name()
    if kitchen is None:
        raise click.ClickException('You are not in a Kitchen')
    recipe_dir = DKRecipeDisk.find_recipe_root_dir()
    if recipe_dir is None:
        raise click.ClickException('You must be in a Recipe folder')
    recipe_name = DKRecipeDisk.find_recipe_name()
    click.secho("%s - Getting the status of Recipe '%s' in Kitchen '%s'\n\tversus directory '%s'" % (
        get_datetime(), recipe_name, kitchen, recipe_dir), fg='green')
    check_and_print(DKCloudCommandRunner.recipe_status(backend.dki, kitchen, recipe_name, recipe_dir))

# --------------------------------------------------------------------------------------------------------------------
# User and Authentication Commands
# --------------------------------------------------------------------------------------------------------------------
@dk.command(name='user-info')
@click.pass_obj
def user_info(backend):
    """
    Get information about this user.
    """
    check_and_print(DKCloudCommandRunner.user_info(backend.dki))


# --------------------------------------------------------------------------------------------------------------------
#  kitchen commands
# --------------------------------------------------------------------------------------------------------------------
def get_datetime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@dk.command(name='kitchen-list')
@click.pass_obj
def kitchen_list(backend):
    """
    List all Kitchens
    """
    click.echo(click.style('%s - Getting the list of kitchens' % get_datetime(), fg='green'))
    check_and_print(DKCloudCommandRunner.list_kitchen(backend.dki))


@dk.command(name='kitchen-get')
@click.option('--recipe', '-r', type=str, multiple=True, help='Get the recipe along with the kitchen. Multiple allowed')
@click.option('--all','-a',is_flag=True,help='Get all recipes along with the kitchen.')
@click.argument('kitchen_name', required=True)
@click.pass_obj
def kitchen_get(backend, kitchen_name, recipe, all):
    """
    Get an existing Kitchen locally. You may also get one or multiple Recipes from the Kitchen.
    """
    found_kitchen = DKKitchenDisk.find_kitchen_name()
    if found_kitchen is not None and len(found_kitchen) > 0:
        raise click.ClickException("You cannot get a kitchen into an existing kitchen directory structure.")

    if len(recipe) > 0:
        click.secho("%s - Getting kitchen '%s' and the recipes %s" % (get_datetime(), kitchen_name, str(recipe)), fg='green')
    else:
        click.secho("%s - Getting kitchen '%s'" % (get_datetime(), kitchen_name), fg='green')

    check_and_print(DKCloudCommandRunner.get_kitchen(backend.dki, kitchen_name, os.getcwd(), recipe, all))


@dk.command(name='kitchen-which')
@click.pass_obj
def kitchen_which(backend):
    """
    What Kitchen am I working in?
    """
    check_and_print(DKCloudCommandRunner.which_kitchen(backend.dki, None))


@dk.command(name='kitchen-create')
@click.argument('kitchen', required=True)
@click.option('--parent', '-p', type=str, required=True, help='name of parent kitchen')
@click.option('--description', '-d', type=str, required=False, help='Kitchen description')
@click.pass_obj
def kitchen_create(backend, parent, description, kitchen):
    """
    Create and name a new child Kitchen. Provide parent Kitchen name.
    """

    if not DKCloudCommandRunner.kitchen_exists(backend.dki, parent):
        raise click.ClickException('Parent kitchen %s does not exists. Check spelling.' % parent)

    click.secho('%s - Creating kitchen %s from parent kitchen %s' % (get_datetime(), kitchen, parent), fg='green')
    master = 'master'
    if kitchen.lower() != master.lower():
        check_and_print(DKCloudCommandRunner.create_kitchen(backend.dki, parent, kitchen, description))
    else:
        raise click.ClickException('Cannot create a kitchen called %s' % master)


@dk.command(name='kitchen-delete')
@click.argument('kitchen', required=True)
@click.option('--yes', '-y', default=False, is_flag=True, required=False, help='Force yes')
@click.pass_obj
def kitchen_delete(backend, kitchen, yes):
    """
    Provide the name of the kitchen to delete
    """

    try:
        DKCloudCommandRunner.print_kitchen_children(backend.dki, kitchen)
    except Exception as e:
        raise click.ClickException(e.message)

    if not yes:
        confirm = raw_input('\nAre you sure you want to delete the remote copy of the Kitchen %s ? [yes/No]' % kitchen)
        if confirm.lower() != 'yes':
            return

    click.secho('%s - Deleting remote copy of kitchen %s. Local files will not change.' % (get_datetime(), kitchen), fg='green')
    master = 'master'
    if kitchen.lower() != master.lower():
        check_and_print(DKCloudCommandRunner.delete_kitchen(backend.dki, kitchen))
    else:
        raise click.ClickException('Cannot delete the kitchen called %s' % master)


@dk.command(name='kitchen-config')
@click.option('--kitchen', '-k', type=str, required=False, help='kitchen name')
@click.option('--add', '-a', type=str, required=False, nargs=2,
              help='Add a new override to this kitchen. This will update an existing override variable.\n'
                   'Usage: --add VARIABLE VALUE\n'
                   'Example: --add kitchen_override \'value1\'',
              multiple=True)
@click.option('--get', '-g', type=str, required=False, help='Get the value for an override variable.', multiple=True)
@click.option('--unset', '-u', type=str, required=False, help='Delete an override variable.', multiple=True)
@click.option('--listall', '-la', type=str, is_flag=True, required=False, help='List all variables and their values.')
@click.pass_obj
def kitchen_config(backend, kitchen, add, get, unset, listall):
    """
    Get and Set Kitchen variable overrides

    Example:
    dk kf -k Dev_Sprint -a kitchen_override 'value1'
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    check_and_print(DKCloudCommandRunner.config_kitchen(backend.dki, use_kitchen, add, get, unset, listall))


@dk.command(name='kitchen-merge-preview')
@click.option('--source_kitchen', '-sk', type=str, required=False, help='source (from) kitchen name')
@click.option('--target_kitchen', '-tk', type=str, required=True, help='target (to) kitchen name')
@click.option('--clean_previous_run', '-cpr', default=False, is_flag=True, required=False, help='Clean previous run of this command')
@click.pass_obj
def kitchen_merge_preview(backend, source_kitchen, target_kitchen, clean_previous_run):
    """
    Preview the merge of two Kitchens. No change will actually be applied.
    Provide the names of the Source (Child) and Target (Parent) Kitchens.
    """

    try:
        kitchen = DKCloudCommandRunner.which_kitchen_name()
        if kitchen is None and source_kitchen is None:
            raise click.ClickException('You are not in a Kitchen and did not specify a source_kitchen')

        if kitchen is not None and source_kitchen is not None and kitchen != source_kitchen:
            raise click.ClickException('There is a conflict between the kitchen in which you are, and the source_kitchen you have specified')

        if kitchen is not None:
            use_source_kitchen = kitchen
        else:
            use_source_kitchen = source_kitchen

        kitchens_root = DKKitchenDisk.find_kitchens_root(reference_kitchen_names=[use_source_kitchen, target_kitchen])
        if kitchens_root:
            DKCloudCommandRunner.check_local_recipes(backend.dki, kitchens_root, use_source_kitchen)
            DKCloudCommandRunner.check_local_recipes(backend.dki, kitchens_root, target_kitchen)
        else:
            click.secho('The root path for your kitchens was not found, skipping local checks.')

        click.secho('%s - Previewing merge Kitchen %s into Kitchen %s' % (get_datetime(), use_source_kitchen, target_kitchen), fg='green')
        check_and_print(DKCloudCommandRunner.kitchen_merge_preview(backend.dki, use_source_kitchen, target_kitchen, clean_previous_run))
    except Exception as e:
        error_message = e.message
        if 'Recipe' in e.message and 'does not exist on remote.' in e.message:
            error_message += ' Delete your local copy before proceeding.'
        raise click.ClickException(error_message)

@dk.command(name='kitchen-merge')
@click.option('--source_kitchen', '-sk', type=str, required=False, help='source (from) kitchen name')
@click.option('--target_kitchen', '-tk', type=str, required=True, help='target (to) kitchen name')
@click.option('--yes', '-y', default=False, is_flag=True, required=False, help='Force yes')
@click.pass_obj
def kitchen_merge(backend, source_kitchen, target_kitchen, yes):
    """
    Merge two Kitchens. Provide the names of the Source (Child) and Target (Parent) Kitchens.
    """
    try:
        kitchen = DKCloudCommandRunner.which_kitchen_name()
        if kitchen is None and source_kitchen is None:
            raise click.ClickException('You are not in a Kitchen and did not specify a source_kitchen')

        if kitchen is not None and source_kitchen is not None and kitchen != source_kitchen:
            raise click.ClickException('There is a conflict between the kitchen in which you are, and the source_kitchen you have specified')

        if kitchen is not None:
            use_source_kitchen = kitchen
        else:
            use_source_kitchen = source_kitchen

        kitchens_root = DKKitchenDisk.find_kitchens_root(reference_kitchen_names=[use_source_kitchen, target_kitchen])
        if kitchens_root:
            DKCloudCommandRunner.check_local_recipes(backend.dki, kitchens_root, use_source_kitchen)
            DKCloudCommandRunner.check_local_recipes(backend.dki, kitchens_root, target_kitchen)
        else:
            click.secho('The root path for your kitchens was not found, skipping local checks.')

        if not yes:
            confirm = raw_input('Are you sure you want to merge the \033[1mremote copy of Source Kitchen %s\033[0m into the \033[1mremote copy of Target Kitchen %s\033[0m? [yes/No]'
                                % (use_source_kitchen, target_kitchen))
            if confirm.lower() != 'yes':
                return

        click.secho('%s - Merging Kitchen %s into Kitchen %s' % (get_datetime(), use_source_kitchen, target_kitchen), fg='green')
        check_and_print(DKCloudCommandRunner.kitchen_merge(backend.dki, use_source_kitchen, target_kitchen))

        DKCloudCommandRunner.update_local_recipes_with_remote(backend.dki, kitchens_root, target_kitchen)
    except Exception as e:
        raise click.ClickException(e.message)


# --------------------------------------------------------------------------------------------------------------------
#  Recipe commands
# --------------------------------------------------------------------------------------------------------------------
@dk.command(name='recipe-list')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.pass_obj
def recipe_list(backend, kitchen):
    """
    List the Recipes in a Kitchen
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    click.secho("%s - Getting the list of Recipes for Kitchen '%s'" % (get_datetime(), use_kitchen), fg='green')
    check_and_print(DKCloudCommandRunner.list_recipe(backend.dki, use_kitchen))

@dk.command(name='recipe-create')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--template', '-tm', type=str, help='template name')
@click.argument('name', required=True)
@click.pass_obj
def recipe_create(backend, kitchen, name, template):
    """
    Create a new Recipe
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    click.secho("%s - Creating Recipe %s for Kitchen '%s'" % (get_datetime(), name, use_kitchen), fg='green')
    check_and_print(DKCloudCommandRunner.recipe_create(backend.dki, use_kitchen, name, template=template))

@dk.command(name='recipe-delete')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--yes', '-y', default=False, is_flag=True, required=False, help='Force yes')
@click.argument('name', required=True)
@click.pass_obj
def recipe_delete(backend,kitchen,name, yes):
    """
    Deletes local and remote copy of the given recipe
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)

    click.secho("This command will delete the local and remote copy of recipe '%s' for kitchen '%s'. " % (name, use_kitchen))
    if not yes:
        confirm = raw_input('Are you sure you want to delete the local and remote copy of recipe %s? [yes/No]' % name)
        if confirm.lower() != 'yes':
            return

    click.secho("%s - Deleting Recipe %s for Kitchen '%s'" % (get_datetime(), name, use_kitchen), fg='green')
    check_and_print(DKCloudCommandRunner.recipe_delete(backend.dki, use_kitchen,name))

@dk.command(name='recipe-get')
@click.option('--force', '-f', default=False, is_flag=True, required=False, help='Force remote version of Recipe')
@click.argument('recipe', required=False)
@click.pass_obj
def recipe_get(backend, recipe, force):
    """
    Get the latest files for a Recipe.
    If a local copy of the Recipe exists the --force option will wipe the local version and sync to the remote version.
    If a local copy of the Recipe exists and updates have been applied to both local and remote versions of files, without causing conflicts, these changes will be auto-merged.
    However, if these changes result in conflicts, recipe-get will write to said files both versions so that the user can manually resolve conflicts.
    Local vs remote conflicts are best reviewed (but not edited) via the file-diff command.
    """
    recipe_root_dir = DKRecipeDisk.find_recipe_root_dir()
    if recipe_root_dir is None:
        if recipe is None:
            raise click.ClickException("\nPlease change to a recipe folder or provide a recipe name arguement")

        # raise click.ClickException('You must be in a Recipe folder')
        kitchen_root_dir = DKKitchenDisk.is_kitchen_root_dir()
        if not kitchen_root_dir:
            raise click.ClickException("\nPlease change to a recipe folder or a kitchen root dir.")
        recipe_name = recipe
        start_dir = DKKitchenDisk.find_kitchen_root_dir()
    else:
        recipe_name = DKRecipeDisk.find_recipe_name()
        if recipe is not None:
            if recipe_name != recipe:
                raise click.ClickException("\nThe recipe name argument '%s' is inconsistent with the current directory '%s'" % (recipe, recipe_root_dir))
        start_dir = recipe_root_dir

    kitchen_name = Backend.get_kitchen_name_soft()
    click.secho("%s - Getting the latest version of Recipe '%s' in Kitchen '%s'" % (get_datetime(), recipe_name, kitchen_name), fg='green')
    check_and_print(DKCloudCommandRunner.get_recipe(backend.dki, kitchen_name, recipe_name, start_dir, force=force))

@dk.command(name='recipe-compile')
@click.option('--variation', '-v', type=str, required=True, help='variation name')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--recipe', '-r', type=str, help='recipe name')
@click.pass_obj
def recipe_compile(backend, kitchen, recipe, variation):
    """
    Apply variables to a Recipe
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)

    if recipe is None:
        recipe = DKRecipeDisk.find_recipe_name()
        if recipe is None:
            raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')

    click.secho('%s - Get the Compiled Recipe %s.%s in Kitchen %s' % (get_datetime(), recipe, variation, use_kitchen),
                fg='green')
    check_and_print(DKCloudCommandRunner.get_compiled_serving(backend.dki, use_kitchen, recipe, variation))

@dk.command(name='file-compile')
@click.option('--variation', '-v', type=str, required=True, help='variation name')
@click.option('--file', '-f', type=str, required=True, help='file path')
@click.pass_obj
def file_compile(backend, variation, file):
    """
    Apply variables to a File
    """
    kitchen = DKCloudCommandRunner.which_kitchen_name()
    if kitchen is None:
        raise click.ClickException('You are not in a Kitchen')

    recipe_dir = DKRecipeDisk.find_recipe_root_dir()
    if recipe_dir is None:
        raise click.ClickException('You must be in a Recipe folder')
    recipe_name = DKRecipeDisk.find_recipe_name()

    click.secho('%s - Get the Compiled File of Recipe %s.%s in Kitchen %s' % (get_datetime(), recipe_name, variation, kitchen),
                fg='green')
    check_and_print(DKCloudCommandRunner.get_compiled_file(backend.dki, kitchen, recipe_name, variation, file))


@dk.command(name='file-history')
@click.option('--change_count', '-cc', type=int, required=False, default=0, help='Number of last changes to display')
@click.argument('filepath', required=True)
@click.pass_obj
def file_resolve(backend, change_count, filepath):
    """
    Show file change history.
    """
    kitchen = DKCloudCommandRunner.which_kitchen_name()
    if kitchen is None:
        raise click.ClickException('You are not in a Kitchen')

    recipe = DKRecipeDisk.find_recipe_name()
    if recipe is None:
        raise click.ClickException('You must be in a recipe folder.')

    click.secho("%s - Retrieving file history" % get_datetime())

    if not os.path.exists(filepath):
        raise click.ClickException('%s does not exist' % filepath)
    check_and_print(DKCloudCommandRunner.file_history(backend.dki, kitchen,recipe,filepath,change_count))


@dk.command(name='recipe-validate')
@click.option('--variation', '-v', type=str, required=True, help='variation name')
@click.pass_obj
def recipe_validate(backend, variation):
    """
    Validates local copy of a recipe, returning a list of errors and warnings. If there are no local changes, will only
    validate remote files.

    """
    kitchen = DKCloudCommandRunner.which_kitchen_name()
    if kitchen is None:
        raise click.ClickException('You are not in a Kitchen')
    recipe_dir = DKRecipeDisk.find_recipe_root_dir()
    if recipe_dir is None:
        raise click.ClickException('You must be in a Recipe folder')
    recipe_name = DKRecipeDisk.find_recipe_name()

    click.secho('%s - Validating recipe/variation %s.%s in Kitchen %s' % (get_datetime(), recipe_name, variation, kitchen),
                fg='green')
    check_and_print(DKCloudCommandRunner.recipe_validate(backend.dki, kitchen, recipe_name, variation))

@dk.command(name='recipe-variation-list')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--recipe', '-r', type=str, help='recipe name')
@click.pass_obj
def recipe_variation_list(backend, kitchen, recipe):
    """
    Shows the available variations for the current recipe in a kitchen
    """
    recipe_local = DKRecipeDisk.find_recipe_name()
    if recipe_local is None:
        get_remote = True
        err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
        if use_kitchen is None:
            raise click.ClickException(err_str)
        if recipe is None:
            raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')
        use_recipe = Backend.remove_slashes(recipe)
        click.secho('Getting variations from remote ...', fg='green')
    else:
        get_remote = False
        use_recipe = recipe_local
        use_kitchen = DKCloudCommandRunner.which_kitchen_name()
        if use_kitchen is None:
            raise click.ClickException('You are not in a Kitchen')
        click.secho('Getting variations from local ...', fg='green')

    if not DKCloudCommandRunner.kitchen_exists(backend.dki, use_kitchen):
        raise click.ClickException('Kitchen %s does not exists. Check spelling.' % use_kitchen)

    click.secho('%s - Listing variations for recipe %s in Kitchen %s' % (get_datetime(), use_recipe, use_kitchen), fg='green')
    check_and_print(DKCloudCommandRunner.recipe_variation_list(backend.dki, use_kitchen, use_recipe, get_remote))

@dk.command(name='recipe-ingredient-list')
@click.pass_obj
def recipe_variation_list(backend):
    """
    Shows the available ingredients for the current recipe in a kitchen
    """
    kitchen = DKCloudCommandRunner.which_kitchen_name()
    if kitchen is None:
        raise click.ClickException('You are not in a Kitchen')
    print kitchen
    recipe_dir = DKRecipeDisk.find_recipe_root_dir()
    if recipe_dir is None:
        raise click.ClickException('You must be in a Recipe folder')
    recipe_name = DKRecipeDisk.find_recipe_name()

    click.secho('%s - Listing ingredients for recipe %s in Kitchen %s' % (get_datetime(), recipe_name, kitchen),
                fg='green')
    check_and_print(DKCloudCommandRunner.recipe_ingredient_list(backend.dki, kitchen, recipe_name))

# --------------------------------------------------------------------------------------------------------------------
#  File commands
# --------------------------------------------------------------------------------------------------------------------
@dk.command(name='file-diff')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--recipe', '-r', type=str, help='recipe name')
@click.argument('filepath', required=True)
@click.pass_obj
def file_diff(backend, kitchen, recipe, filepath):
    """
    Show differences with remote version of the file

    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    recipe_dir = DKRecipeDisk.find_recipe_root_dir()
    if recipe_dir is None:
        raise click.ClickException('You must be in a Recipe folder')
    if recipe is None:
        recipe = DKRecipeDisk.find_recipe_name()
        if recipe is None:
            raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')

    click.secho('%s - File Diff for file %s, in Recipe (%s) in Kitchen (%s)' %
                (get_datetime(), filepath, recipe, use_kitchen), fg='green')
    check_and_print(DKCloudCommandRunner.file_diff(backend.dki, use_kitchen, recipe, recipe_dir, filepath))

@dk.command(name='file-merge')
@click.option('--source_kitchen', '-sk', type=str, required=False, help='source (from) kitchen name')
@click.option('--target_kitchen', '-tk', type=str, required=True, help='target (to) kitchen name')
@click.argument('filepath', required=True)
@click.pass_obj
def file_merge(backend, source_kitchen, target_kitchen, filepath):
    """
    To be used after kitchen-merge-preview command.
    Launch the merge tool of choice, to resolve conflicts.

    """
    kitchen = DKCloudCommandRunner.which_kitchen_name()
    if kitchen is None and source_kitchen is None:
        raise click.ClickException('You are not in a Kitchen and did not specify a source_kitchen')

    if kitchen is not None and source_kitchen is not None and kitchen != source_kitchen:
        raise click.ClickException('There is a conflict between the kitchen in which you are, and the source_kitchen you have specified')

    if kitchen is not None:
        use_source_kitchen = kitchen
    else:
        use_source_kitchen = source_kitchen

    click.secho('%s - File Merge for file %s, source kitchen (%s), target kitchen(%s)' %
                (get_datetime(), filepath, use_source_kitchen, target_kitchen), fg='green')
    check_and_print(DKCloudCommandRunner.file_merge(backend.dki, filepath, use_source_kitchen, target_kitchen))

@dk.command(name='file-resolve')
@click.option('--source_kitchen', '-sk', type=str, required=False, help='source (from) kitchen name')
@click.option('--target_kitchen', '-tk', type=str, required=True, help='target (to) kitchen name')
@click.argument('filepath', required=True)
@click.pass_obj
def file_resolve(backend, source_kitchen, target_kitchen, filepath):
    """
    Mark a conflicted file as resolved, so that a merge can be completed
    """
    kitchen = DKCloudCommandRunner.which_kitchen_name()
    if kitchen is None and source_kitchen is None:
        raise click.ClickException('You are not in a Kitchen and did not specify a source_kitchen')

    if kitchen is not None and source_kitchen is not None and kitchen != source_kitchen:
        raise click.ClickException('There is a conflict between the kitchen in which you are, and the source_kitchen you have specified')

    if kitchen is not None:
        use_source_kitchen = kitchen
    else:
        use_source_kitchen = source_kitchen

    click.secho("%s - File resolve for file %s, source kitchen (%s), target kitchen(%s)" %
                (get_datetime(), filepath, use_source_kitchen, target_kitchen))
    check_and_print(DKCloudCommandRunner.file_resolve(backend.dki, use_source_kitchen, target_kitchen, filepath))

@dk.command(name='file-get')
@click.argument('filepath', required=True)
@click.pass_obj
def file_get(backend, filepath):
    """
    Get the latest version of a file from the server and overwriting your local copy.
    """
    kitchen = DKCloudCommandRunner.which_kitchen_name()
    if kitchen is None:
        raise click.ClickException('You must be in a Kitchen')
    recipe = DKRecipeDisk.find_recipe_name()
    if recipe is None:
        raise click.ClickException('You must be in a recipe folder.')

    click.secho('%s - Getting File (%s) to Recipe (%s) in kitchen(%s)' %
                (get_datetime(), filepath, recipe, kitchen), fg='green')
    check_and_print(DKCloudCommandRunner.get_file(backend.dki, kitchen, recipe, filepath))


@dk.command(name='file-update')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--recipe', '-r', type=str, help='recipe name')
@click.option('--message', '-m', type=str, required=True, help='change message')
@click.argument('filepath', required=True, nargs=-1)
@click.pass_obj
def file_update(backend, kitchen, recipe, message, filepath):
    """
    Update a Recipe file
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    recipe_dir = DKRecipeDisk.find_recipe_root_dir()
    if recipe_dir is None:
        raise click.ClickException('You must be in a Recipe folder')
    if recipe is None:
        recipe = DKRecipeDisk.find_recipe_name()
        if recipe is None:
            raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')

    click.secho('%s - Updating File(s) (%s) in Recipe (%s) in Kitchen(%s) with message (%s)' %
                (get_datetime(), filepath, recipe, use_kitchen, message), fg='green')
    check_and_print(DKCloudCommandRunner.update_file(backend.dki, use_kitchen, recipe, recipe_dir, message, filepath))


@dk.command(name='recipe-update')
@click.option('--delete_remote', '-d', default=False, is_flag=True, required=False, help='Delete remote files to match local')
@click.option('--message', '-m', type=str, required=True, help='change message')
@click.pass_obj
def file_update_all(backend, message, delete_remote):
    """
    Update all of the changed files for this Recipe
    """
    kitchen = DKCloudCommandRunner.which_kitchen_name()
    if kitchen is None:
        raise click.ClickException('You must be in a Kitchen')
    recipe_dir = DKRecipeDisk.find_recipe_root_dir()
    if recipe_dir is None:
        raise click.ClickException('You must be in a Recipe folder')
    recipe = DKRecipeDisk.find_recipe_name()

    click.secho('%s - Updating all changed files in Recipe (%s) in Kitchen(%s) with message (%s)' %
                (get_datetime(), recipe, kitchen, message), fg='green')
    check_and_print(DKCloudCommandRunner.update_all_files(backend.dki, kitchen, recipe, recipe_dir, message, delete_remote=delete_remote))


@dk.command(name='file-delete')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--recipe', '-r', type=str, help='recipe name')
@click.option('--message', '-m', type=str, required=True, help='change message')
@click.argument('filepath', required=True, nargs=-1)
@click.pass_obj
def file_delete(backend, kitchen, recipe, message, filepath):
    """
    Delete one or more Recipe files. If you are not in a recipe path, provide the file path(s) relative to the recipe root.
    Separate multiple file paths with spaces.  File paths need no preceding backslash.

    Example...

    dk file-delete -m "my delete message" file1.json dir2/file2.json
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    if recipe is None:
        recipe = DKRecipeDisk.find_recipe_name()
        if recipe is None:
            raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')

    click.secho('%s - Deleting (%s) in Recipe (%s) in kitchen(%s) with message (%s)' %
                (get_datetime(), filepath, recipe, use_kitchen, message), fg='green')
    check_and_print(DKCloudCommandRunner.delete_file(backend.dki, use_kitchen, recipe, message, filepath))

# --------------------------------------------------------------------------------------------------------------------
#  Active Serving commands
# --------------------------------------------------------------------------------------------------------------------

@dk.command(name='active-serving-watcher')
@click.option('--kitchen','-k', type=str, required=False, help='Kitchen name')
@click.option('--interval', '-i', type=int, required=False, default=5, help='watching interval, in seconds')
@click.pass_obj
def active_serving_watcher(backend, kitchen, interval):
    """
    Watches all cooking Recipes in a Kitchen. Provide the Kitchen name as an argument or be in a Kitchen folder. Optionally provide a watching period as an integer, in seconds. Ctrl+C to terminate.
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    click.secho('%s - Watching Active OrderRun Changes in Kitchen %s' % (get_datetime(), use_kitchen), fg='green')
    DKCloudCommandRunner.watch_active_servings(backend.dki, use_kitchen, interval)
    while True:
        try:
            DKCloudCommandRunner.join_active_serving_watcher_thread_join()
            if not DKCloudCommandRunner.watcher_running():
                break
        except KeyboardInterrupt:
            print 'KeyboardInterrupt'
            exit_gracefully(None, None)
    exit(0)


# --------------------------------------------------------------------------------------------------------------------
#  Order commands
# --------------------------------------------------------------------------------------------------------------------

@dk.command(name='order-run')
@click.argument('variation', required=True)
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--recipe', '-r', type=str, help='recipe name')
@click.option('--node', '-n', type=str, required=False, help='Name of the node to run')
@click.option('--yes', '-y', default=False, is_flag=True, required=False, help='Force yes')
@click.pass_obj
def order_run(backend, kitchen, recipe, variation, node, yes):
    """
    Run an order: cook a recipe variation
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    if recipe is None:
        recipe = DKRecipeDisk.find_recipe_name()
        if recipe is None:
            raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')

    if not yes:
        confirm = raw_input('Kitchen %s, Recipe %s, Variation %s.\n'
                            'Are you sure you want to run an Order? [yes/No]'
                            % (use_kitchen, recipe, variation))
        if confirm.lower() != 'yes':
            return

    msg = '%s - Create an Order:\n\tKitchen: %s\n\tRecipe: %s\n\tVariation: %s\n' % (get_datetime(), use_kitchen, recipe, variation)
    if node is not None:
        msg += '\tNode: %s\n' % node

    click.secho(msg, fg='green')
    check_and_print(DKCloudCommandRunner.create_order(backend.dki, use_kitchen, recipe, variation, node))


@dk.command(name='order-delete')
@click.option('--kitchen', '-k', type=str, default=None, help='kitchen name')
@click.option('--order_id', '-o', type=str, default=None, help='Order ID')
@click.option('--yes', '-y', default=False, is_flag=True, required=False, help='Force yes')
@click.pass_obj
def order_delete(backend, kitchen, order_id, yes):
    """
    Delete one order or all orders in a kitchen
    """
    use_kitchen = Backend.get_kitchen_name_soft(kitchen)
    print use_kitchen
    if use_kitchen is None and order_id is None:
        raise click.ClickException('You must specify either a kitchen or an order_id or be in a kitchen directory')

    if not yes:
        if order_id is None:
            confirm = raw_input('Are you sure you want to delete all Orders in kitchen %s ? [yes/No]' % use_kitchen)
        else:
            confirm = raw_input('Are you sure you want to delete Order %s ? [yes/No]' % order_id)
        if confirm.lower() != 'yes':
            return

    if order_id is not None:
        click.secho('%s - Delete an Order using id %s' % (get_datetime(), order_id), fg='green')
        check_and_print(DKCloudCommandRunner.delete_one_order(backend.dki, order_id))
    else:
        click.secho('%s - Delete all orders in Kitchen %s' % (get_datetime(), use_kitchen), fg='green')
        check_and_print(DKCloudCommandRunner.delete_all_order(backend.dki, use_kitchen))


@dk.command(name='order-stop')
@click.option('--order_id', '-o', type=str, required=True, help='Order ID')
@click.option('--yes', '-y', default=False, is_flag=True, required=False, help='Force yes')
@click.pass_obj
def order_stop(backend, order_id, yes):
    """
    Stop an order - Turn off the serving generation ability of an order.  Stop any running jobs.  Keep all state around.
    """
    if order_id is None:
        raise click.ClickException('invalid order id %s' % order_id)

    if not yes:
        confirm = raw_input('Are you sure you want to stop Order %s? [yes/No]' % order_id)
        if confirm.lower() != 'yes':
            return

    click.secho('%s - Stop order id %s' % (get_datetime(), order_id), fg='green')
    check_and_print(DKCloudCommandRunner.stop_order(backend.dki, order_id))


@dk.command(name='orderrun-stop')
@click.option('--order_run_id', '-ori', type=str, required=True, help='OrderRun ID')
@click.option('--yes', '-y', default=False, is_flag=True, required=False, help='Force yes')
@click.pass_obj
def order_stop(backend, order_run_id, yes):
    """
    Stop the run of an order - Stop the running order and keep all state around.
    """
    if order_run_id is None:
        raise click.ClickException('invalid order id %s' % order_run_id)

    if not yes:
        confirm = raw_input('Are you sure you want to stop Order-Run %s ? [yes/No]' % order_run_id)
        if confirm.lower() != 'yes':
            return

    click.secho('%s - Stop order id %s' % (get_datetime(), order_run_id), fg='green')
    check_and_print(DKCloudCommandRunner.stop_orderrun(backend.dki, order_run_id.strip()))


@dk.command(name='orderrun-info')
@click.option('--kitchen', '-k', type=str, help='kitchen name')
@click.option('--order_id', '-o', type=str, default=None, help='Order ID')
@click.option('--order_run_id', '-ori', type=str, default=None, help='OrderRun ID to display')
@click.option('--summary', '-s', default=False, is_flag=True, required=False, help='display run summary information')
@click.option('--nodestatus', '-ns', default=False, is_flag=True, required=False, help=' display node status info')
@click.option('--log', '-l', default=False, is_flag=True, required=False, help=' display log info')
@click.option('--timing', '-t', default=False, is_flag=True, required=False, help='display timing results')
@click.option('--test', '-q', default=False, is_flag=True, required=False, help='display test results')
@click.option('--runstatus', default=False, is_flag=True, required=False,
              help=' display status of the run (single line)')
@click.option('--disp_order_id', default=False, is_flag=True, required=False,
              help=' display the order id (single line)')
@click.option('--disp_order_run_id', default=False, is_flag=True, required=False,
              help=' display the order run id (single line)')
@click.option('--all_things', '-at', default=False, is_flag=True, required=False, help='display all information')
# @click.option('--recipe', '-r', type=str, help='recipe name')
@click.pass_obj
def orderrun_detail(backend, kitchen, summary, nodestatus, runstatus, log, timing, test, all_things,
                    order_id, order_run_id, disp_order_id, disp_order_run_id):
    """
    Display information about an Order-Run
    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)
    # if recipe is None:
    #     recipe = DKRecipeDisk.find_reciper_name()
    #     if recipe is None:
    #         raise click.ClickException('You must be in a recipe folder, or provide a recipe name.')
    pd = dict()
    if all_things:
        pd['summary'] = True
        pd['logs'] = True
        pd['timingresults'] = True
        pd['testresults'] = True
        # pd['state'] = True
        pd['status'] = True
    if summary:
        pd['summary'] = True
    if log:
        pd['logs'] = True
    if timing:
        pd['timingresults'] = True
    if test:
        pd['testresults'] = True
    if nodestatus:
        pd['status'] = True

    if runstatus:
        pd['runstatus'] = True
    if disp_order_id:
        pd['disp_order_id'] = True
    if disp_order_run_id:
        pd['disp_order_run_id'] = True

    # if the user does not specify anything to display, show the summary information
    if not runstatus and \
            not all_things and \
            not test and \
            not timing and \
            not log and \
            not nodestatus and \
            not summary and \
            not disp_order_id and \
            not disp_order_run_id:
        pd['summary'] = True

    if order_id is not None and order_run_id is not None:
        raise click.ClickException("Cannot specify both the Order Id and the OrderRun Id")
    if order_id is not None:
        pd[DKCloudCommandRunner.ORDER_ID] = order_id.strip()
    elif order_run_id is not None:
        pd[DKCloudCommandRunner.ORDER_RUN_ID] = order_run_id.strip()

    # don't print the green thing if it is just runstatus
    if not runstatus and not disp_order_id and not disp_order_run_id:
        click.secho('%s - Display Order-Run details from kitchen %s' % (get_datetime(), use_kitchen), fg='green')
    check_and_print(DKCloudCommandRunner.orderrun_detail(backend.dki, use_kitchen, pd))


@dk.command('orderrun-delete')
@click.argument('orderrun_id', required=True)
@click.option('--yes', '-y', default=False, is_flag=True, required=False, help='Force yes')
@click.pass_obj
def delete_orderrun(backend, orderrun_id, yes):
    """
    Delete the orderrun specified by the argument.
    """
    if orderrun_id is None:
        raise click.ClickException('invalid order id %s' % orderrun_id)

    if not yes:
        confirm = raw_input('Are you sure you want to delete Order-Run  %s ? [yes/No]' % orderrun_id)
        if confirm.lower() != 'yes':
            return

    click.secho('%s - Deleting orderrun %s' % (get_datetime(), orderrun_id), fg='green')
    check_and_print(DKCloudCommandRunner.delete_orderrun(backend.dki, orderrun_id.strip()))


@dk.command('orderrun-resume')
@click.argument('orderrun_id', required=True)
@click.option('--yes', '-y', default=False, is_flag=True, required=False, help='Force yes')
@click.pass_obj
def order_resume(backend, orderrun_id, yes):
    """
    Resumes a failed order run
    """
    if orderrun_id is None:
        raise click.ClickException('invalid order id %s' % orderrun_id)

    if not yes:
        confirm = raw_input('Are you sure you want to resume Order-Run %s ? [yes/No]' % orderrun_id)
        if confirm.lower() != 'yes':
            return

    click.secho('%s - Resuming Order-Run %s' % (get_datetime(), orderrun_id), fg='green')
    check_and_print(DKCloudCommandRunner.order_resume(backend.dki, orderrun_id.strip()))


@dk.command(name='order-list')
@click.option('--kitchen', '-k', type=str, required=False, help='Filter results for kitchen only')
@click.option('--start', '-s', type=int, required=False, default=0, help='Start offset for displaying orders')
@click.option('--order_count', '-oc', type=int, required=False, default=5, help='Number of orders to display')
@click.option('--order_run_count', '-orc', type=int, required=False, default=3, help='Number of order runs to display, for each order')
@click.option('--recipe', '-r', type=str, required=False, default=None, help='Filter results for this recipe only')
@click.pass_obj
def order_list(backend, kitchen, order_count, order_run_count, start, recipe):
    """
    List Orders in a Kitchen.

    Examples:

    1) Basic usage with no paging, 5 orders, 3 order runs per order.

    dk order-list

    2) Get first, second and third page, ten orders per page, two order runs per order.

    dk order-list --start 0  --order_count 10 --order_run_count 2

    dk order-list --start 10 --order_count 10 --order_run_count 2

    dk order-list --start 20 --order_count 10 --order_run_count 2

    3) Get first five orders per page, two order runs per order, for recipe recipe_name

    dk order-list --recipe recipe_name --order_count 5 --order_run_count 2

    """
    err_str, use_kitchen = Backend.get_kitchen_from_user(kitchen)
    if use_kitchen is None:
        raise click.ClickException(err_str)

    if order_count <= 0:
        raise click.ClickException('order_count must be an integer greater than 0')

    if order_run_count <= 0:
        raise click.ClickException('order_count must be an integer greater than 0')

    click.secho('%s - Get Order information for Kitchen %s' % (get_datetime(), use_kitchen), fg='green')

    check_and_print(
            DKCloudCommandRunner.list_order(backend.dki, use_kitchen, order_count, order_run_count, start, recipe=recipe))

# --------------------------------------------------------------------------------------------------------------------
#  Secret commands
# --------------------------------------------------------------------------------------------------------------------
@dk.command(name='secret-list')
@click.option('--recursive', '-rc', is_flag=True, required=False, help='Recursive')
@click.argument('path', required=False)
@click.pass_obj
def secret_list(backend,path,recursive):
    """
    List all Secrets
    """
    click.echo(click.style('%s - Getting the list of secrets' % get_datetime(), fg='green'))
    check_and_print(
        DKCloudCommandRunner.secret_list(backend.dki,path,recursive))

@dk.command(name='secret-write')
@click.argument('entry',required=True)
@click.option('--yes', '-y', default=False, is_flag=True, required=False, help='Force yes')
@click.pass_obj
def secret_write(backend,entry,yes):
    """
    Write one secret to the Vault. Spaces are not allowed. Wrap values in single quotes.

    Example: dk secret-write standalone-credential='test-credential'

    """
    path,value=entry.split('=')

    if value.startswith('@'):
        with open(value[1:]) as vfile:
            value = vfile.read()

    # Check if path already exists
    rc = DKCloudCommandRunner.secret_exists(backend.dki, path, print_to_console=False)
    if rc.ok() and rc.get_message():
        secret_exists = True
    elif rc.ok():
        secret_exists = False
    else:
        raise click.ClickException(rc.get_message())

    # If secret already exists, prompt confirmation message
    if secret_exists:
        if not yes:
            confirm = raw_input('Are you sure you want to overwrite the existing Vault Secret %s ? [yes/No]' % path)
            if confirm.lower() != 'yes':
                return

    click.echo(click.style('%s - Writing secret' % get_datetime(), fg='green'))
    check_and_print(DKCloudCommandRunner.secret_write(backend.dki,path,value))

@dk.command(name='secret-delete')
@click.argument('path', required=True)
@click.option('--yes', '-y', default=False, is_flag=True, required=False, help='Force yes')
@click.pass_obj
def secret_delete(backend,path, yes):
    """
    Delete a secret
    """
    if path is None:
        raise click.ClickException('invalid path %s' % path)

    if not yes:
        confirm = raw_input('Are you sure you want to delete Secret %s? [yes/No]' % path)
        if confirm.lower() != 'yes':
            return

    click.echo(click.style('%s - Deleting secret' % get_datetime(), fg='green'))
    check_and_print(
        DKCloudCommandRunner.secret_delete(backend.dki,path))

@dk.command(name='secret-exists')
@click.argument('path', required=True)
@click.pass_obj
def secret_delete(backend,path):
    """
    Checks if a secret exists
    """
    click.echo(click.style('%s Checking secret' % get_datetime(), fg='green'))
    check_and_print(
        DKCloudCommandRunner.secret_exists(backend.dki,path))


@dk.command(name='kitchen-settings-get')
@click.pass_obj
def kitchen_settings_get(backend):
    """
    Get Kitchen Settings (kitchen-settings.json) for your customer account.
    This file is global to all Kitchens.  Your role must equal "IT" to get
    the kitchen-settings.json file.
    """

    if not backend.dki.is_user_role('IT'):
        raise click.ClickException('You have not IT privileges to run this command')

    kitchen = 'master'

    click.secho("%s - Getting a local copy of kitchen-settings.json" % get_datetime(), fg='green')
    check_and_print(DKCloudCommandRunner.kitchen_settings_get(backend.dki, kitchen))


@dk.command(name='kitchen-settings-update')
@click.argument('filepath', required=True, nargs=-1)
@click.pass_obj
def kitchen_settings_update(backend, filepath):
    """
    Upload Kitchen Settings (kitchen-settings.json) for your customer account.
    This file is global to all Kitchens.  Your role must equal "IT" to upload
    the kitchen-settings.json file.
    """

    if not backend.dki.is_user_role('IT'):
        raise click.ClickException('You have not IT privileges to run this command')


    kitchen = 'master'

    click.secho("%s - Updating the settings" % get_datetime(), fg='green')
    check_and_print(DKCloudCommandRunner.kitchen_settings_update(backend.dki, kitchen, filepath))

original_sigint = None

def _get_repo_root_dir(directory):

    if not directory or directory == '/':
        return None
    elif os.path.isdir(os.path.join(directory,'.git')):
        return directory

    parent,_ = os.path.split(directory)
    return _get_repo_root_dir(parent)


HOOK_FILES = ['pre-commit']
GITHOOK_TEMPLATE = """
#!/bin/bash
python -m DKCloudCommand.hooks.DKHooks $0 "$@"
exit $?
"""

def _install_hooks(hooks_dir):

    for hook in HOOK_FILES:
        pre_commit_file = os.path.join(hooks_dir,hook)

        with open(pre_commit_file,'w') as f:
            f.write(GITHOOK_TEMPLATE)

        os.chmod(pre_commit_file,stat.S_IXUSR|stat.S_IRUSR|stat.S_IWUSR)

def _setup_user(repo_dir,config):
    import subprocess
    user = config.get_username()

    subprocess.check_output(['git','config','--local','user.name',user])
    subprocess.check_output(['git','config','--local','user.email',user])

@dk.command(name='git-setup')
@click.pass_obj
def git_setup(backend):
    """
    Set up a GIT repository for DK CLI.
    """
    repo_root_dir = _get_repo_root_dir(os.getcwd())

    if not repo_root_dir:
        raise click.ClickException('You are not in a git repository')

    hooks_dir = os.path.join(repo_root_dir,'.git','hooks')

    _install_hooks(hooks_dir)
    _setup_user(repo_root_dir,backend.dki.get_config())
    pass

# http://stackoverflow.com/questions/18114560/python-catch-ctrl-c-command-prompt-really-want-to-quit-y-n-resume-executi
def exit_gracefully(signum, frame):
    global original_sigint
    # print 'exit_gracefully'
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    DKCloudCommandRunner.stop_watcher()
    # print 'exit_gracefully stopped watcher'
    signal(SIGINT, original_sigint)
    question = False
    if question is True:
        try:
            if raw_input("\nReally quit? (y/n)> ").lower().startswith('y'):
                exit(1)
        except (KeyboardInterrupt, SystemExit):
            print("Ok ok, quitting")
            exit(1)
    else:
        print("Ok ok, quitting now")
        DKCloudCommandRunner.join_active_serving_watcher_thread_join()
        exit(1)
    # restore the exit gracefully handler here
    signal(SIGINT, exit_gracefully)


# https://chriswarrick.com/blog/2014/09/15/python-apps-the-right-way-entry_points-and-scripts/
def main(args=None):
    global original_sigint

    if args is None:
        args = sys.argv[1:]
        Backend()   # force to check version

    # store the original SIGINT handler
    original_sigint = getsignal(SIGINT)
    signal(SIGINT, exit_gracefully)

    dk()


# if __name__ == '__main__':
#     # store the original SIGINT handler
#     original_sigint = getsignal(SIGINT)
#     signal(SIGINT, exit_gracefully)
#     dk()

if __name__ == "__main__":
    main()
