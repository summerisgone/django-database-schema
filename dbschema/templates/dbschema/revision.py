# -*- coding: utf-8 -*-

from django.conf import settings
from django.db import connection, transaction

@transaction.autocommit
def upgrade():
    # prepare here
    # prepare end
    transaction.commit()
    try:
        connection.cursor().execute('''
-- upgrade query here

{{ upgrade_sql|safe }}
-- upgrade query end
''')
        transaction.commit()
    except StandardError, error:
        transaction.rollback()
        # fail here
        # fail end
        return error
    # post processing here
    # post processing end
    return None

@transaction.autocommit
def downgrade():
    # prepare here
    # prepare end
    transaction.commit()
    try:
        connection.cursor().execute('''
-- downgrade query here

{{ downgrade_sql|safe }}
-- downgrade query end
''')
        transaction.commit()
    except StandardError, error:
        transaction.rollback()
        # fail here
        # fail end
        return error
    # post processing here
    # post processing end
    return None
