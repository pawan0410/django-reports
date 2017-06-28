from mssql.connections import EMRSQLServer
from emr.models import Status

class FormatStatus:

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "{}".format(self.name.title())


def get_status():
    rows = EMRSQLServer().execute_query("SELECT APPOINTMENTSTATUSID, STATUS from APPOINTMENTSTATUS")
    return {row['APPOINTMENTSTATUSID']:  str(FormatStatus(row['STATUS'])) for row in rows if row['STATUS'] != 'NONE'}


def load_status_into_table():
    rows = get_status()
    for row, v in rows.items():
        s = Status(original_id=row, name=v)
        s.save()

