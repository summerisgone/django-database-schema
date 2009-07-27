# -*- coding: utf-8 -*-

from rs.dbschema.models import Repository

from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = '''Usage manage.py dbschema [command]
    Manage database schema revisions.
    
Available commands:
    apply [revno]           Apply given schema revision to database
    add                     Create empty revision file from template and 
                            append it to schema. You will need only edit 
                            revision file
    revno                   Print current database schema revision number
    log                     Log local repository
    count                   Print how much revisions you have
    forcerevno <revno>      Override revision number in database
    forceupgrade <revno>    Execute upgrade function form revno revision
    forcedowngrade <revno>  Execute dowgrade function form revno revision
    init <app1 [app2 ...]>  Create revision with SQL script to create 
                            tables for applications (as sqlall command).
    initall                 Create revision with script to create all tables 
                            for all applications (as syncdb command).
                            P.S: check references:
                            some references can be commented,
                            some references can be used before definition. 
    reset                   Reset schema configuration
    '''

    def handle(self, *args, **options):
        if not args:
            print self.help
            return
        command = args[0]
        if command == 'add':
            Repository.add()
        elif command == 'apply':
            try:
                revno = int(args[1])
            except ValueError:
                raise CommandError('Usage: apply [revno]')
            except IndexError:
                revno = Repository.count()
            if revno == Repository.get_revno():
                print 'Already upgraded.'
            Repository.apply(revno)
        elif command == 'revno':
            print Repository.get_revno()
        elif command == 'count':
            print Repository.count()
        elif command == 'log':
            revno = Repository.get_revno()
            revisions = Repository.get_revisions()
            revisions.insert(0, '[None]')
            for index, revision in enumerate(revisions):
                if index == revno:
                    current = '*'
                else:
                    current = ' '
                print '%s%4d:\t%s' % (current, index, revision)
        elif command == 'forcerevno':
            try:
                revno = int(args[1])
            except (ValueError, IndexError):
                raise CommandError('Usage: forcerevno [revno]')
            Repository.set_revno(revno)
        elif command == 'forceupgrade' or command == 'forcedowngrade':
            revisions = Repository.get_revisions()
            try:
                revision = revisions[int(args[1])]
            except (ValueError, IndexError):
                raise CommandError('Usage: %s <revno>' % command)
            print '%s -' % revision,
            result = Repository.execute(revision, command == 'forceupgrade')
            if result is None:
                print 'OK.'
            else:
                print 'Fail.'
                print result
        elif command == 'reset':
            print 'Reseting will drop revstore configuration, enter "y" to confirm'
            ans = raw_input()
            if ans == 'y':
                Repository.reset()
                print 'Done.'
            elif ans == 'n':
                print 'Good decision. Bye!'
        elif command == 'init':
            application_names = args[1:]
            if application_names:
                Repository.init(application_names)
            else:
                raise CommandError('Usage: %s <revno>' % command)
        elif command == 'initall':
            Repository.initall()
            print '''P.S: check references:
some references can be commented,
some references can be used before definition.'''
        else:
            print self.help
