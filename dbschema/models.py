# -*- coding: utf-8 -*-

import os
import re
import sys
from datetime import datetime, timedelta
from os.path import join, dirname, abspath, exists, split

from django.core.management.sql import sql_all, sql_delete
from django.core.management.color import no_style
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

TEMPLATE_DIR = dirname(abspath(__file__))
if hasattr(settings, 'REVSTORE_DIR'):
    REVSTORE_DIR = settings.REVSTORE_DIR
else:
    REVSTORE_DIR = join(dirname(dirname(dirname(abspath(__file__)))), 'revstore')
    
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
    def make_dir(cls):
        if not exists(REVSTORE_DIR):
            os.makedirs(REVSTORE_DIR)
            open(join(REVSTORE_DIR, '__init__.py'), 'w')
    
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
        insert = REVSTORE_DIR not in sys.path
        if insert:
            sys.path.insert(0, REVSTORE_DIR)
        try:
            module = __import__('sequence', globals(), locals(), [''])
            result = module.revisions
        except ImportError:
            result = []
        if insert:
            sys.path.remove(REVSTORE_DIR)
        return result

    @classmethod
    def set_revisions(cls, revisions):
        '''
            Update revision list
        '''
        template_file = open(join(TEMPLATE_DIR, 'sequence.template'), 'r')
        template = template_file.read()
        cls.make_dir()
        init_file = open(join(REVSTORE_DIR, 'sequence.py'), 'w')
        init_file.write(template % (
            '[\n%s]' % ',\n'.join([repr(revision)
                for revision in revisions] + [''])))

    @classmethod
    def count(cls):
        return len(cls.get_revisions())

    @classmethod
    def execute(cls, revision, upgrade=True):
        insert = REVSTORE_DIR not in sys.path
        if insert:
            sys.path.insert(0, REVSTORE_DIR)
        try:
            module = __import__(revision, globals(), locals(), ['upgrade', 'downgrade'])
        except ImportError:
            module = None
        if insert:
            sys.path.remove(REVSTORE_DIR)
        if module is None:
            print 'Can`t find revision'
            return False
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
        template_file = open(join(TEMPLATE_DIR, 'revision.template'), 'r')
        template = template_file.read().encode('utf-8')

        userid = 'unknown'
        for var in ['USER', 'USERNAME']:
            userid = os.environ.get(var, userid)
        userid = re.sub(r'[^A-Za-z0-9]', '_', userid)
        time = datetime.now()
        while True:
            revision = 'revision_%s_%s' % (
                time.strftime('%Y_%m_%d__%H_%M'), userid)

            cls.make_dir()
            revision_name = join(REVSTORE_DIR, '%s.py' % revision)
            if not exists(revision_name):
                revision_file = open(revision_name, 'w')
                revision_file.write(template % (upgrade_sql, downgrade_sql))
                break
            time = time + timedelta(minutes=1)

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
