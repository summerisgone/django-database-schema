# -*- coding: utf-8 -*-

import os
import re
import sys
from datetime import datetime, timedelta

from django.core.management.sql import sql_all, sql_delete
from django.core.management.color import no_style
from django.conf import settings
from django.db import models, connection, transaction
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string

REVSTORE_DIR = getattr(settings, 'REVSTORE_DIR', None)
if REVSTORE_DIR is None:
    module = __import__(os.environ['DJANGO_SETTINGS_MODULE'], {}, {}, [])
    REVSTORE_DIR = os.path.join(os.path.dirname(os.path.abspath(module.__file__)), 'revstore')

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
        if not os.path.exists(REVSTORE_DIR):
            os.makedirs(REVSTORE_DIR)
            open(os.path.join(REVSTORE_DIR, '__init__.py'), 'w').close()
    
    @classmethod
    @transaction.commit_manually
    def create_table(cls):
        '''
            Create tables for dbschema
        '''
        transaction.commit()
        application = models.get_app('dbschema')
        sql = ''.join(sql_all(application, no_style()))
        try:
            connection.cursor().execute(sql)
            transaction.commit()
        except StandardError, error:
            # Tables already exists 
            transaction.rollback()
    
    @classmethod
    def set_revno(cls, revno):
        '''
            Sets given revision number in database
        '''
        cls.create_table()
        cls.objects.create(revno=revno)

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
        
        cls.make_dir()
        name = os.path.join(REVSTORE_DIR, 'sequence.py')
        file = open(name, 'w')
        file.write(render_to_string('dbschema/sequence.py', {'revisions': revisions}))

    @classmethod
    def count(cls):
        return len(cls.get_revisions())

    @classmethod
    def get_revision_obj(cls, module):
        # Here we are looking for a variable called 'Revision' in the revision module
        # if it's found we assume that it's a new (class-based) revision format
        #
        # If it's not found, then we assume an old revision format and 
        # construct a 'DummyRevision' object which calls upgrade() and
        # downgrade() functions from the revision module.
        if hasattr(module, 'Revision'):
            revision = module.Revision()
        else:
            revision = DummyRevision(module.upgrade, module.downgrade)
        return revision

    @classmethod
    def execute(cls, revision, upgrade=True):
        insert = REVSTORE_DIR not in sys.path
        if insert:
            sys.path.insert(0, REVSTORE_DIR)
        try:
            module = __import__(revision, globals(), locals(), [])
        except ImportError:
            module = None
        if insert:
            sys.path.remove(REVSTORE_DIR)
        if module is None:
            print 'Can`t find revision'
            return False
        revision = cls.get_revision_obj(module)
        if upgrade:
            return revision.upgrade()
        else:
            return revision.downgrade()

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
        userid = 'unknown'
        for var in ['USER', 'USERNAME']:
            userid = os.environ.get(var, userid)
        userid = re.sub(r'[^A-Za-z0-9]', '_', userid)
        time = datetime.now()
        while True:
            revision = 'revision_%s_%s' % (
                time.strftime('%Y_%m_%d__%H_%M'), userid)

            cls.make_dir()
            name = os.path.join(REVSTORE_DIR, '%s.py' % revision)
            if not os.path.exists(name):
                file = open(name, 'w')
                file.write(render_to_string('dbschema/revision.py', {
                    'upgrade_sql': upgrade_sql, 
                    'downgrade_sql': downgrade_sql,
                }))
                break
            time = time + timedelta(minutes=1)

        revisions = cls.get_revisions()
        revisions.append(revision)
        cls.set_revisions(revisions)

        print 'New revision was added, change it:\n%s' % name

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
