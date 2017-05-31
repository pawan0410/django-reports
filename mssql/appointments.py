from mssql.connections import EMRSQLServer
from emr.models import AppointmentType


def get_appointment_type():
    rows = EMRSQLServer().execute_query("EXEC GetAllAppointmentTypes")
    return {row['APPOINTMENTTYPEID']: row['TYPE'] for row in rows}


def load_appointment_type_into_table():
    rows = get_appointment_type()
    for r, v in rows.items():
        appointment = AppointmentType(original_id=r, name=v)
        appointment.save()