#!/usr/bin/env python

import codecs

from sys import argv
from hashlib import sha1
from cStringIO import StringIO


class githash(object):
    def __init__(self):
        self.buf = StringIO()

    def update(self, data):
        self.buf.write(data)

    def hexdigest(self):
        data = self.buf.getvalue()
        h = sha1()
        h.update("blob %u\0" % len(data))
        h.update(data)

        return h.hexdigest()


def githash_data(data):
    h = githash()
    h.update(data)
    return h.hexdigest()


def githash_by_file_name(file_name):
    with codecs.open(file_name, 'r', encoding='utf-8') as f:
        file_contents = f.read()
        return githash_data(file_contents.encode('utf-8'))


if __name__ == '__main__':
    for filename in argv[1:]:
        print(githash_by_file_name(filename))
