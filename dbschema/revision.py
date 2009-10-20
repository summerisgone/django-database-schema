from django.db import transaction, connection

class BaseRevision(object):
    """
    This class is designed to be subclassed.
    Define upgrade_sql and downgrade_sql attributes in the inherited class.
    Override methods as needed.
    """

    upgrade_sql = ''
    downgrade_sql = ''

    def execute_sql(self, sql):
        cursor = connection.cursor()
        cursor.execute(sql)
        return cursor

    def upgrade_postprocessing(self):
        pass

    def downgrade_postprocessing(self):
        pass

    @transaction.commit_manually
    def upgrade(self):
        try:
            self.execute_sql(self.upgrade_sql)
            self.upgrade_postprocessing()
            transaction.commit()
        except:
            transaction.rollback()
            raise

    @transaction.commit_manually
    def downgrade(self):
        try:
            self.execute_sql(self.downgrade_sql)
            self.downgrade_postprocessing()
            transaction.commit()
        except:
            transaction.rollback()
            raise


class DummyRevision(BaseRevision):
    def __init__(self, upgrade, downgrade):
        self.upgrade = upgrade
        self.downgrade = downgrade

    def upgrade(self):
        self.upgrade()

    def downgrade(self):
        self.downgrade()

