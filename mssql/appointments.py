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


def get_resource_utilization_slots():
    slots_group = ResourceUtilizationSlots.objects.all()
    return {r.resource_id: \
                {'MON': r.monday, 'TUE': r.tuesday, 'WED': r.wednesday, 'THU': r.thursday, 'FRI': r.friday} \
            for r in slots_group}


def flatten_seen_statuses():
    status_all = StatusGroup.objects.filter(name__iexact='Seen Patients')
    statuses = []
    for s in status_all:
        for i in s.status_id.all():
            statuses.append(i.original_id)
    return statuses


class SeenPatients:

    def __init__(self, from_date, to_date, resource_group_id, appointment_group_id,include_holidays=False):
        self.from_date = from_date
        self.to_date = to_date
        self.resources = get_resources_by_group_id(resource_group_id)
        self.appointment_types = get_appointments_by_appointment_type_id(appointment_group_id)
        self.status_all = flatten_seen_statuses()
        self.resources_slots = get_resource_utilization_slots()
        self.resources_all = get_resource()
        self.include_holidays = include_holidays

    def sql_query(self):
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

        if self.from_date and self.to_date:
            query += " AND APPOINTMENTDATE >= '%s' AND APPOINTMENTDATE <= '%s' " % (self.from_date, self.to_date)

        if self.resources:
            query += " AND A.RESOURCEID IN (%s)" % ','.join([str(r) for r in self.resources])

        if self.appointment_types:
            query += " AND V.APPOINTMENTTYPEID IN (%s)" % ','.join([str(a) for a in self.appointment_types])

        query += " ORDER BY A.STARTTIME"

        return query

    def get_rows_from_query(self):

        query = self.sql_query()
        rows = EMRSQLServer().execute_query(query)
        output = defaultdict(list)
        for row in rows:
            output[row['RESOURCEID']].append(row)

        return output

    def study_details(self):

        output = defaultdict(list)
        output = self.get_rows_from_query()
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

            return studies_by_date, studies_seen ,studies

    def total_slots_for_day(self, week_number, week_day, week_str, resources_slots, resource_id):
        if (self.from_date + datetime.timedelta(days=week_number)).isoweekday() in [6, 7]:
            return

        if (self.from_date + datetime.timedelta(days=week_number)).isoweekday() == week_day:
            try:
                return resources_slots[resource_id][week_str]
            except KeyError:
                return 0

    def get_total_confirmed_studies(self):
        _, studies_seen,_ = self.study_details()
        return sum([len(studies_seen[int(i)]) for i in self.status_all])

    def days_taken_for_studies(self):
        t1 = datetime.datetime.strptime(self.from_date, '%Y-%m-%d')
        t2 = datetime.datetime.strptime(self.to_date, '%Y-%m-%d')

        total_requested_days = (t2 - t1).days + 1
        studies_by_date, _ ,_= self.study_details()

        days_taken_for_studies = len(studies_by_date)
        if self.include_holidays and days_taken_for_studies < total_requested_days:
            days_taken_for_studies += total_requested_days - days_taken_for_studies
        return days_taken_for_studies

    def reports(self):

        number_of_confirmed_studies = self.get_total_confirmed_studies()
        total_slots_for_days = self.total_slots_for_day()
        output = self.get_rows_from_query()
        studies_by_date, _, _ = self.study_details()
        _,_,studies = self.study_details()
        results = []
        for item, value in output.items():

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
                'ResourceName': self.resources_all[item],
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


def appointments(from_date, to_date, resource_group_id=None, appointment_group_id=None, include_holidays=False):

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
    if resources:
        query += " AND A.RESOURCEID IN (%s)" % ','.join([str(r) for r in resources])

    appointment_types = get_appointments_by_appointment_type_id(appointment_group_id)
    if appointment_types:
        query += " AND V.APPOINTMENTTYPEID IN (%s)" % ','.join([str(a) for a in appointment_types])

    query += " ORDER BY A.STARTTIME"

    status_all = flatten_seen_statuses()
    resources_slots = get_resource_utilization_slots()
    resources_all = get_resource()

    results = []
    rows = EMRSQLServer().execute_query(query)

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

        t1 = datetime.datetime.strptime(from_date, '%Y-%m-%d')
        t2 = datetime.datetime.strptime(to_date, '%Y-%m-%d')

        total_requested_days = (t2 - t1).days + 1

        if include_holidays and days_taken_for_studies < total_requested_days:
            days_taken_for_studies += total_requested_days - days_taken_for_studies

        total_slots_for_day = []
        for i in range(total_requested_days):
            if (t1 + datetime.timedelta(days=i)).isoweekday() in [6, 7]:
                continue
            if (t1 + datetime.timedelta(days=i)).isoweekday() == 1:
                try:
                    total_slots_for_day.append(resources_slots[item]['MON'])
                except KeyError:
                    total_slots_for_day.append(0)

            if (t1 + datetime.timedelta(days=i)).isoweekday() == 2:
                try:
                    total_slots_for_day.append(resources_slots[item]['TUE'])
                except KeyError:
                    total_slots_for_day.append(0)

            if (t1 + datetime.timedelta(days=i)).isoweekday() == 3:
                try:
                    total_slots_for_day.append(resources_slots[item]['WED'])
                except KeyError:
                    total_slots_for_day.append(0)

            if (t1 + datetime.timedelta(days=i)).isoweekday() == 4:
                try:
                    total_slots_for_day.append(resources_slots[item]['THU'])
                except KeyError:
                    total_slots_for_day.append(0)

            if (t1 + datetime.timedelta(days=i)).isoweekday() == 5:
                try:
                    total_slots_for_day.append(resources_slots[item]['FRI'])
                except KeyError:
                    total_slots_for_day.append(0)

        total_slots_for_days = sum(total_slots_for_day)  # if all(total_slots_for_day) else 0

        try:
            utilization = (number_of_confirmed_studies * 100) // total_slots_for_days
        except ZeroDivisionError:
            utilization = 0
        total_slots_for_days = resources_slots[item] * days_taken_for_studies
        utilization = (number_of_confirmed_studies * 100) // total_slots_for_days

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
            'scheduled_percentage': '{0}%'.format((len(value) * 100) // total_slots_for_days),
            'number_of_confirmed_studies': number_of_confirmed_studies,
            'seen_percentage': '{0}%'.format((number_of_confirmed_studies * 100) // len(value)),
            'total_slots_in_a_day': total_slots_for_days,
            'color_code': color_code,
            'text_color': text_color
        })
    return results
