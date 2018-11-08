# -*- coding: utf-8 -*-

import os
import platform
import sys
from ctypes import *

if platform.python_version()[0] != '2':
    raise NotImplementedError

reload(sys)
sys.setdefaultencoding('utf-8')


class Tag(Structure):
    _fields_ = [
        ('offset', c_int),
        ('length', c_int),
        ('type', c_char * 32),
        ('type_confidence', c_double)
    ]


class LacTagger(object):
    def __init__(self, conf_dir, max_result_num=99999):
        self.conf_dir = conf_dir
        self.max_result_num = max_result_num
        self.load_library()
        self.build_tag_t()

    def load_library(self):
        self.liblac = pydll.LoadLibrary('liblac.so')

    def _init_dict(self):
        self.lac_handle = self.liblac.lac_create(self.conf_dir)
        print('create lac handle successfully')

    def _destroy_dict(self):
        self.liblac.lac_destroy(self.lac_handle)

    def _init_buf(self):
        self.lac_buff = self.liblac.lac_buff_create(self.lac_handle)
        if not self.lac_buff:
            print('create lac_buff error')
        else:
            print('create lac buff successfully')

    def _destroy_buf(self):
        self.liblac.lac_buff_destroy(self.lac_handle, self.lac_buff)

    def init(self):
        self._init_dict()
        self._init_buf()

    def close(self):
        self._destroy_buf()
        self._destroy_dict()

    def build_tag_t(self):
        self.tag_t = (Tag * self.max_result_num)()

    def tagging(self, line):
        result_num = self.liblac.lac_tagging(self.lac_handle, self.lac_buff,
                                             line,
                                             byref(self.tag_t),
                                             self.max_result_num)

        res = []
        if result_num < 0:
            print('lac tagging failed: line = %s' % line)
        else:
            res = []
            for i in range(result_num):
                result = self.tag_t[i]
                name = line[result.offset:result.offset + result.length]
                name = name.decode('utf-8')
                item = dict(name=name, type=result.type, offset=result.offset,
                            length=result.length)
                res.append(item)

        return res


if __name__ == '__main__':
    tag = LacTagger('../conf')
    tag.init()
    res = tag.tagging('我爱北京天安门')
    print(res)
    tag.close()
