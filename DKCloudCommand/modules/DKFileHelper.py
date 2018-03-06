import os
import shutil
import base64
import json

class DKFileHelper:
    def __init__(self):
        pass

    @staticmethod
    def is_file_contents_binary(file_contents):
        try:
            file_contents.encode('utf8')
            return False
        except:
            return True

    @staticmethod
    def create_dir_if_not_exists(directory):
        if not os.path.exists(directory):
            os.makedirs(directory)

    @staticmethod
    def create_path_if_not_exists(full_path):
        if not os.path.exists(full_path):
            os.makedirs(full_path)

    @staticmethod
    def clear_dir(directory):
        if os.path.exists(directory):
            shutil.rmtree(directory)

    @staticmethod
    def read_file(full_path, encoding=None):
        if not os.path.isfile(full_path):
            return ''
        with open(full_path, 'rb') as the_file:
            file_contents = the_file.read()
            if encoding == 'infer':
                encoding = DKFileHelper.infer_encoding(full_path)
            if encoding == 'base64':
                return base64.b64encode(file_contents)
            else:
                return file_contents

    @staticmethod
    def infer_encoding(full_path):
        ext = full_path.split('.')[-1] if '.' in full_path else full_path
        if ext in ['json', 'txt', 'md', 'sql']:
            return None
        else:
            return 'base64'

    @staticmethod
    def write_file(full_path, contents, encoding=None):
        path, file_name = os.path.split(full_path)
        DKFileHelper.create_path_if_not_exists(path)
        if isinstance(contents, dict):
            contents = json.dumps(contents)
        with open(full_path, 'wb+') as the_file:
            the_file.seek(0)
            the_file.truncate()
            if encoding == 'base64' and contents is not None:
                the_file.write(base64.b64decode(contents))
            elif contents is not None:
                the_file.write(contents)


