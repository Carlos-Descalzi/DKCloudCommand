import os
import base64


class DKFileEncodeHelper:
    B64ENCODE = 'b64encode'
    B64DECODE = 'b64decode'

    BINARY_FILE_EXTENSIONS = ['exe', 'bin',
                              'gzip', 'gz', '7z', 'arc', 'arj', 'lzip', 'lz', 'rar', 'tar', 'tgz', 'z',
                              'iso', 'bkf', 'bzip2', 'bz2', 'zip', 'cab',
                              'jar', 'egg',
                              'deb', 'rpm',
                              'img', 'png', 'jpg', 'gif',
                              'xls', 'xlsx', 'doc', 'docx']

    @staticmethod
    def is_binary(full_path):
        return 'base64' == DKFileEncodeHelper.infer_encoding(full_path)

    @staticmethod
    def infer_encoding(full_path):
        if full_path is None:
            return 'utf-8'
        ext = full_path.split('.')[-1] if '.' in full_path else full_path
        if ext in DKFileEncodeHelper.BINARY_FILE_EXTENSIONS:
            return 'base64'
        return 'utf-8'

    @staticmethod
    def binary_files(operation, the_dict):
        if 'recipes' in the_dict and len(the_dict['recipes']) > 0:
            recipes = the_dict['recipes']
            for recipe_name, recipe_dict in recipes.iteritems():
                for the_path, the_items in recipe_dict.iteritems():
                    for the_item in the_items:
                        if DKFileEncodeHelper.is_binary(the_item['filename']):
                            if DKFileEncodeHelper.B64ENCODE == operation:
                                the_item['text'] = DKFileEncodeHelper.b64encode(the_item['text'])
                            if DKFileEncodeHelper.B64DECODE == operation:
                                the_item['text'] = DKFileEncodeHelper.b64decode(the_item['text'])
        return the_dict

    @staticmethod
    def b64encode(file_contents):
        if file_contents is None:
            return None
        return base64.b64encode(file_contents)

    @staticmethod
    def b64decode(file_contents):
        if file_contents is None:
            return None
        return base64.b64decode(file_contents)

