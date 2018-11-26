#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
import getpass
import os
import yaml


class PopServerInfo(object):

    DEFAULT_INFOFILE='popserver_info.yml'

    def __init__(self, filename=None):
        self.pop_server = 'pop.nifty.com'
        self.account = ''
        self.password = ''


    def input_info(self):
        buffer_pop_server = input(
            'pop3 server({0}):'.format(self.pop_server))
        if buffer_pop_server:
            self.pop_server = buffer_pop_server
        buffer_account = input('login({0}):'.format(self.account)) 
        if buffer_account:
            self.account = buffer_account
        raw_password = getpass.getpass('password:')
        self.password = base64.standard_b64encode(
                raw_password.encode(encoding='utf-8')
                ).decode(encoding='utf-8')

    

    def serialize(self):
        return {
            'pop_server': self.pop_server,
            'account': self.account,
            'password': self.password
        }

    def set_info_from_dic(self, dic):
        self.pop_server = dic('pop_server')
        self.account = dic('account')
        self.password = dic('password')


    def save(self, filename=DEFAULT_INFOFILE):
        with open(filename,'w',encoding='utf-8') as f:
            f.write(yaml.dump(self.serialize()))


    def load(self, filename=DEFAULT_INFOFILE):
        with open(filename,'r',encoding='utf-8') as f:
            self.set_info_from_dic(yaml.load(f))


    def get_pass(self):
        return base64.standard_b64decode(
                self.password.encode(encoding='utf-8')
            ).decode(encoding='utf-8')