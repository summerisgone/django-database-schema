# -*- coding: utf-8 -*-

from dbschema import BaseRevision

class Revision(BaseRevision):
    upgrade_sql = '''
-- upgrade sql begins
{{ upgrade_sql|safe }}
-- upgrade sql ends
'''

    downgrade_sql = '''
-- downgrade sql begins
{{ downgrade_sql|safe }}
-- downgrade sql ends
'''
