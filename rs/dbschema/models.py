# -*- coding: utf-8 -*-

import os
import re
import sys
from datetime import datetime
from os.path import join, dirname, abspath, exists, split

from django.core.management.sql import sql_all, sql_delete
from django.core.management.color import no_style
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

REVSTORE = 'revstore'
REVSTORE_DIR = join(dirname(abspath(__file__)), REVSTORE)

class Repository(models.Model):
    '''
        Class representing database schema repository
    '''
    class Meta:
        db_table = 'dbschema_repository'
        ordering = ['-applied']

    revno = models.IntegerField(verbose_name=_('revision number'), default=0)
    applied = models.DateTimeField(verbose_name=_('applied'), auto_now_add=True)
    
    @classmethod
    def set_revno(cls, revno):
        '''
            Sets given revision number in database
        '''
        try:
            cls.objects.create(revno=revno)
        except StandardError, error:
            # table "dbschema_repository" does not exist
            if revno != 0:
                raise error

    @classmethod
    def get_revno(cls):
        '''
            Gets revision number from database
        '''
        revisions = cls.objects.all()
        try:
            count = revisions.count()
        except StandardError:
            # table "dbschema_repository" does not exist
            return 0
        if count == 0:
            cls.set_revno(0)
            return 0
        return revisions[0].revno

    @classmethod
    def get_revisions(cls):
        '''
            Gets revision list
        '''
        try:
            module = __import__(REVSTORE, globals(), locals(), [''])
            return module.revisions
        except ImportError:
            return []

    @classmethod
    def set_revisions(cls, revisions):
        '''
            Update revision list
        '''
        template_file = open(join(REVSTORE_DIR, '__init__.template'), 'r')
        template = template_file.read()

        init_file = open(join(REVSTORE_DIR, '__init__.py'), 'w')
        init_file.write(template % (
            '[\n%s]' % ',\n'.join([repr(revision) 
                for revision in revisions] + [''])))
        
    @classmethod
    def count(cls):
        return len(cls.get_revisions())

    @classmethod
    def execute(cls, revision, upgrade=True):
        module = __import__('%s.%s' % (REVSTORE, revision), globals(), locals(), 
            ['upgrade', 'downgrade'])
        if upgrade:
            return module.upgrade()
        else:
            return module.downgrade()
    
    @classmethod
    def apply(cls, revno):
        '''
            Applies schema version to database
        '''
        revisions = cls.get_revisions()
        while True:
            current = cls.get_revno()
            if revno == current:
                break
            if revno > current:
                action = 'Upgrade'
                next = current + 1
                revision = revisions[current]
            else:
                action = 'Dowgrade'
                next = current - 1
                revision = revisions[next]
            print '%s: %d -> %d -' % (action, current, next),
            result = cls.execute(revision, revno > current)
            if result is None:
                cls.set_revno(next)
                print 'OK.'
            else:
                print 'Fail.'
                print result
                break

    @classmethod
    def add(cls, upgrade_sql='', downgrade_sql=''):
        '''
            Adds template for next revision and adds it into __init__.py
        '''
        template_file = open(join(REVSTORE_DIR, 'revision.template'), 'r')
        template = template_file.read().encode('utf-8')

        userid = 'unknown'
        for var in ['USER', 'USERNAME']:
            userid = os.environ.get(var, userid)
        userid = re.sub(r'[^A-Za-z0-9]', '_', userid)
        iteration = 0
        while True:
            if iteration:
                postfix = '_%d' % (iteration + 1)
            else:
                postfix = '' 
            revision = 'revision_%s_%s%s' % (
                datetime.now().strftime('%Y_%m_%d__%H_%M'), userid, postfix)
            
            revision_name = join(REVSTORE_DIR, '%s.py' % revision)
            if not exists(revision_name):
                revision_file = open(revision_name, 'w')
                revision_file.write(template % (upgrade_sql, downgrade_sql))
                break
            iteration = iteration + 1
        
        revisions = cls.get_revisions()
        revisions.append(revision)
        cls.set_revisions(revisions)
    
        print 'New revision was added, change it:\n%s' % revision_name
        
    @classmethod
    def init(cls, application_names):
        applications = [models.get_app(application_name) 
            for application_name in application_names]  
        upgrade = u''.join([
            u'\n'.join(sql_all(application, no_style()) + ['']).encode('utf-8')
                for application in applications])
        downgrade = u''.join([u'\n'.join(sql_delete(application, no_style()) + ['']).encode('utf-8')
                for application in applications])
        cls.add(upgrade, downgrade)
        
    @classmethod
    def initall(cls):
        cls.init([application.__name__.split('.')[-2] 
            for application in models.get_apps()])
    
    @classmethod
    def reset(cls):
        '''
            Reset revstore configuration
        '''
        cls.set_revisions([])
        cls.set_revno(0)

    def __unicode__(self):
        return self.version
