# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from smskurs.schema.models import Repository

class Command(BaseCommand):
    help = '''Usage manage.py schema [options] [command]
    Manage database schema revisions.
    Available commands:
    init                Create database table with database schema revision number
    apply [revno]       Apply given schema revision to database
    add                 Create empty revision file from template and append
                        it to schema. You will need only edit revision file
    revno               Print current database schema revision number
    log                 Log local repository
    count               Print how much revisions you have
    forcerevno          Override revision number in database
    reset               Reset schema confuguration
    '''

    def handle(self, *args, **options):
        repository = Repository()
        if not args:
            print self.help
            return
        command = args[0]
        if command == 'init':
            repository.initdb()
        elif command == 'add':
            repository.add()
        elif command == 'apply':
            try:
                revno = int(args[1])
                repository.apply(revno)
            except (ValueError, IndexError):
                raise CommandError('Usage: apply [revno]')
        elif command == 'revno':
            print 'Current revision: %s' % repository.revstore.current
        elif command == 'count':
            print len(repository.revisions)
        elif command == 'log':
            print repository.revstore.revision_list
        elif command == 'forcerevno':
            try:
                revno = int(args[1])
                repository.forcerevno(revno)
            except (ValueError, IndexError):
                raise CommandError('Usage: forcerevno [revno]')
        elif command == 'reset':
            print 'Reseting will drop revstore configuration, enter "y" to confirm'
            ans = raw_input()   
            if ans == 'y':
                repository.reset()
            elif ans == 'n':
                print 'Good desigion. Bye!'
        else:
            print self.help
