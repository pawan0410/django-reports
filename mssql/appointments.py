from mssql.connections import EMRSQLServer
from emr.models import AppointmentType
from collections import defaultdict
import datetime
from emr.models import ResourceUtilizationSlots
from emr.models import ResourceGroup
from emr.models import StatusGroup
from emr.models import AppointmentTypeGroup
from mssql.resource import get_resource



def get_appointment_type():
    rows = EMRSQLServer().execute_query("EXEC GetAllAppointmentTypes")
    return {row['APPOINTMENTTYPEID']: row['TYPE'] for row in rows}


def load_appointment_type_into_table():
    rows = get_appointment_type()
    for r, v in rows.items():
        appointment = AppointmentType(original_id=r, name=v)
        appointment.save()


def get_resources_by_group_id(id):
    resource_group = ResourceGroup.objects.filter(id__exact=id)
    resources = []
    for r in resource_group:
        for rs in r.resource_id.all():
            resources.append(rs.original_id)
    return resources

def get_appointments_by_appointment_type_id(id):
    appointment_group = AppointmentTypeGroup.objects.filter(id__exact=id)
    appointments = []
    for r in appointment_group:
        for rs in r.appointment_type_id.all():
            appointments.append(rs.original_id)
    return appointments





def appointments(from_date, to_date, resource_group_id=None, appointment_type_group=None, include_holidays=False):
    """ This method returns the appointments of resources
    in key - value form
    """


    query = """
    SELECT A.STARTTIME, A.ENDTIME, V.APPOINTMENTTYPEID, V.TYPE, \
    A.RESOURCEID, APPOINTMENTDATE, S.STATUS, S.APPOINTMENTSTATUSID
    FROM PATIENT P
    JOIN PATIENT_APPOINTMENTS AS A ON P.PATIENTID = A.PATIENTID
    JOIN APPOINTMENTTYPE AS V ON a.APPOINTMENTTYPEID = v.APPOINTMENTTYPEID
    LEFT OUTER JOIN APPOINTMENTSTATUS AS S ON A.APPOINTMENTSTATUSID = S.APPOINTMENTSTATUSID
    left join (PATIENTINSURANCE PAI
    join INSURANCE_TYPE IT on IT.INSURANCE_TYPE_ID=PAI.INSURANCE_TYPEID
    join INSURANCE_COMPANY IC on IC.INSURANCE_COMPANY_ID=PAI.INSURANCE_COMPANY_ID)
    on P.PatientID=PAI.PATIENTID  and PAI.INSURANCE_TYPEID=1 and PAI.ACTIVE = 1
    WHERE V.APPOINTMENTTYPEID = A.APPOINTMENTTYPEID AND P.PATIENTID = A.PATIENTID
    AND A.ACTIVE = 1
    """

    if from_date and to_date:
        query += " AND APPOINTMENTDATE >= '%s' AND APPOINTMENTDATE <= '%s' " % (from_date, to_date)

    resources = get_resources_by_group_id(resource_group_id)
    appointments = get_appointments_by_appointment_type_id(appointment_type_group)

    query += " AND A.RESOURCEID IN (%s)" % ','.join([str(r) for r in resources])

    if appointment_types:
        query += " AND V.APPOINTMENTTYPEID IN (%s)" % ','.join([str(a) for a in appointment_types])

    query += " ORDER BY A.STARTTIME"

    print(query)
    results = []
    rows = EMRSQLServer().execute_query(query)

    output = defaultdict(list)
    for row in rows:
        output[row['RESOURCEID']].append(row)
    for item, value in output.items():
        studies = defaultdict(list)
        for i, v in enumerate(output[item]):
            studies_start_date = v['APPOINTMENTDATE'].strftime('%Y-%m-%d')
            studies[item].append({
                'name': v['TYPE'],
                'start_time': v['STARTTIME'],
                'end_time': v['ENDTIME'],
                'studies_start_date': studies_start_date,
                'status': v['STATUS'],
                'APPOINTMENTSTATUSID': v['APPOINTMENTSTATUSID']
            })

        studies_by_date = defaultdict(list)
        studies_seen = defaultdict(list)
        for st in studies[item]:
            studies_by_date[st['studies_start_date']].append({
                'name': st['name'],
                'start_time': st['start_time'].strftime('%H:%M:%S'),
                'end_time': st['end_time'].strftime('%H:%M:%S'),
                'status': st['status']
            })
            studies_seen[st['APPOINTMENTSTATUSID']].append({
                'name': st['name'],
                'start_time': st['start_time'].strftime('%H:%M:%S'),
                'end_time': st['end_time'].strftime('%H:%M:%S'),
                'status': st['status']
            })

        number_of_confirmed_studies = sum([len(studies_seen[int(i)]) for i in status_all])
        days_taken_for_studies = len(studies_by_date)

        t1 = datetime.datetime.strptime(to_date, '%Y-%m-%d')
        t2 = datetime.datetime.strptime(from_date, '%Y-%m-%d')

        total_requested_days = (t1-t2).days+1

        if include_holidays and days_taken_for_studies < total_requested_days:
            days_taken_for_studies += total_requested_days - days_taken_for_studies
        else:
            days_taken_for_studies = days_taken_for_studies

        total_slots_for_days = resources_slots[item] * days_taken_for_studies
        try:
            utilization = (number_of_confirmed_studies * 100) // total_slots_for_days
        except ZeroDivisionError:
            utilization = 0

        if utilization <= 79:
            color_code, text_color = '#d9534f', 'white'
        elif (utilization >= 80) and (utilization <= 89):
            color_code, text_color = '#ffe14b', 'black'
        elif utilization >= 90:
            color_code, text_color = '#3c903d', 'white'

        try:
            scheduled_percentage = (len(value) * 100) // total_slots_for_days
        except ZeroDivisionError:
            scheduled_percentage = 0

        try:
            seen_percentage = (number_of_confirmed_studies * 100) // len(value)
        except ZeroDivisionError:
            seen_percentage = 0

        results.append({
            'ResourceID': item,
            'ResourceName': resources_all[item],
            'TotalStudies': len(value),
            'Studies': studies[item],
            'studies_by_date': studies_by_date,
            'utilization': '{0}%'.format(utilization),
            'scheduled_percentage': '{0}%'.format(scheduled_percentage),
            'number_of_confirmed_studies': number_of_confirmed_studies,
            'seen_percentage': '{0}%'.format(seen_percentage),
            'total_slots_in_a_day': total_slots_for_days,
            'color_code': color_code,
            'text_color': text_color
        })
    return results
