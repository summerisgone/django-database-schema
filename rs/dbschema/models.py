# -*- coding: utf-8 -*-

from django.conf import settings
from django.db import models, connection, DatabaseError
from os.path import join, dirname
from datetime import datetime
import sys

# revision filename template:
REVSTORE = 'revstore'
REVISIOIN_FILENAME = 'revision_' + datetime.now().strftime('%Y_%m_%d_%H_%M') + '.py'

class Repository(models.Model):
    '''
        Class representing database schema repository
    '''
    version = models.IntegerField(verbose_name='Database schema version')
    revisions = []
    path = join(settings.PROJECT_DIR, 'schema')

    def __init__(self, *args, **kwrgs):
        # set schema path, or by default use schema directory
        self.revstore = self._import_revisions()
        # get revision list from __init__, useful for merges
        for revision in self.revstore.revision_list:
            self.revisions.append(getattr(self.revstore, revision))
        
        kwrgs['id'] = 1  # only one record
        models.Model.__init__(self, *args, **kwrgs)

    def _import_revisions(self):
        '''
            Do import revisions from self.revision_list
        '''
        revstore = __import__('revstore', globals(), locals())
        modules = __import__('revstore', globals(), locals(),
                             revstore.revision_list)
        return modules

    def _write_init_file(self):
        '''
            Update content in __init__.py file
        '''
        init_file = open(join(self.path, 'revstore/__init__.py'), 'w')

        template_file = open(join(self.path, 'revstore/__init__.template'), 'r')
        template = template_file.read()

        init_file.write(template % {'revision_list': self.revstore.revision_list,
                                    'current': self.revstore.current})

    def _set_revno(self, revno):
        '''
            Set given revision number in database
        '''
        self.version = revno
        self.save()

    def is_uptodate(self):
        return self.version == self.revstore.current

    def apply(self, revno):
        '''
            Applies schema version to database if exists
        '''
        cursor = connection.cursor()

        if revno > self.revstore.current:
        # uprgade database 
            upgrade_list = self.revisions[self.revstore.current:revno]
            print 'upgrade: ', upgrade_list
            
            for revision in upgrade_list:
                try:
                    print 'Upgrade to revision: ', revision.number
                    revision.upgrade(cursor)
                    connection.connection.commit()
                    self.forcerevno(revno)
                except Exception, e:
                    print 'Database Error: %s. Rollback' % e
                    connection.connection.rollback()

        # downgrade database 
        elif revno < self.revstore.current:
            downgrade_list = self.revisions[revno:self.revstore.current]
            downgrade_list.reverse()
            print 'downgrade: ', downgrade_list
            
            for revision in downgrade_list:
                try:
                    print 'Downgrade from revision ', revision.number
                    revision.downgrade(cursor)
                    connection.connection.commit()
                    self.forcerevno(revno)
                except Exception, e:
                    print 'Database Error: %s. Rollback' % e
                    connection.connection.rollback()

    def add(self):
        '''
            Adds template for next revision and adds it into __init__.py
        '''
        template_file = open(join(self.path, 'revstore/revision.template'), 'r')
        template = template_file.read()

        upgrade = '-- upgrade query here'
        downgrade = '-- downgrade query here'

        new_revision_number = len(self.revstore.revision_list) + 1
        new_revision_filename = join(REVSTORE, REVISIOIN_FILENAME)
        new_revision = open(join(self.path, new_revision_filename), 'w')
        new_revision.write(template % {'number': new_revision_number,
                                       'upgrade': upgrade,
                                       'downgrade': downgrade,
                                       })
        # update changes in current revstore.revision_list
        self.revstore.revision_list.append(REVISIOIN_FILENAME[:-3])
        # import newly added revision as module
        new_revision_module = __import__(new_revision_filename[:-3],
                                         globals(), locals())
        # add it to revstore and to repository
        setattr(self.revstore,
                REVISIOIN_FILENAME[:-3],
                new_revision_module
                )
        self.revisions.append(new_revision_module)
        # write changes to disk
        self._write_init_file()
        print join(self.path, new_revision_filename), ' revision added, change it'

    def forcerevno(self, revno):
        '''
            Force database revision number
        '''
        self._set_revno(revno)
        self.revstore.current = revno
        self._write_init_file()

    def reset(self):
        '''
            Reset revstore configuration
        '''
        self._set_revno(0)
        self.revstore.current = 0
        self.revstore.revision_list = []
        self._write_init_file()