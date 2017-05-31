from mssql.connections import EMRSQLServer
from emr.models import Resource

def get_resource():
    rows= EMRSQLServer().execute_query('EXEC GetResource @OnlyActive = 1')
    return {row['RESOURCEID'] : str(row['RESOURCENAME']) for row in rows}

def load_resources_in_table():
    rows = get_resource()
    for id,name in rows.items():
        s = Resource(original_id= id,name = name)
        s.save()