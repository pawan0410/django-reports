import pymssql


class EMRSQLServer:
    """
    A Class for establishing connection with Medstreaming Database
    """
    @staticmethod
    def connection():
        try:
            return pymssql.connect(
                '192.168.3.116',
                'mednet\m.atul',
                'emr@12345678',
                'MedstreamingEMRDB'
            )
        except pymssql.OperationalError as e:
            print(e)

    def __execute_query(self, query, var_dict):
        results = []
        with self.connection().cursor(as_dict=True) as cursor:
            cursor.execute(query, var_dict)
            for row in cursor:
                results.append(row)
        return results

    def execute_query(self, query, var_dict=True, update=False):
        results = []
        with self.connection() as connection:
            results = self.__execute_query(query, var_dict)
            if update:
                connection.commit()
        return results


class HRMSSQLServer:
    """
    A Class for establishing connection with HRMS Database
    """

    #TODO @PawanPreet ..
    pass




