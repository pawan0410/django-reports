from mssql.connections import EMRSQLServer
from emr.models import AppointmentType
from collections import defaultdict


def get_appointment_type():
    rows = EMRSQLServer().execute_query("EXEC GetAllAppointmentTypes")
    return {row['APPOINTMENTTYPEID']: row['TYPE'] for row in rows}


def load_appointment_type_into_table():
    rows = get_appointment_type()
    for r, v in rows.items():
        appointment = AppointmentType(original_id=r, name=v)
        appointment.save()


def appointments(resources_slots, from_date, to_date, resources=[], status_all=[], resources_all={}):
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

    if resources:
        query += " AND A.RESOURCEID IN (%s)" % ','.join([str(r) for r in resources])

    query += " ORDER BY A.STARTTIME"
    results = []
    if not EMRSQLServer.connection():
        return results

    rows = EMRSQLServer.execute_query(query)

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
        total_slots_for_days = resources_slots[item] * days_taken_for_studies
        utilization = (number_of_confirmed_studies * 100) // total_slots_for_days

        if utilization <= 79:
            color_code, text_color = '#d9534f', 'white'
        elif (utilization >= 80) and (utilization <= 89):
            color_code, text_color = '#ffe14b', 'black'
        elif utilization >= 90:
            color_code, text_color = '#3c903d', 'white'

        results.append({
            'ResourceID': item,
            'ResourceName': resources_all[item],
            'TotalStudies': len(value),
            'Studies': studies[item],
            'studies_by_date': studies_by_date,
            'utilization': '{0}%'.format(utilization),
            'scheduled_percentage': '{0}%'.format((len(value) * 100) // total_slots_for_days),
            'number_of_confirmed_studies': number_of_confirmed_studies,
            'seen_percentage': '{0}%'.format((number_of_confirmed_studies * 100) // len(value)),
            'total_slots_in_a_day': total_slots_for_days,
            'color_code': color_code,
            'text_color': text_color
        })
    return results

