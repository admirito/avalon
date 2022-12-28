import ast
import re

from . import BaseMedia


def _import_sql_libs():
    global sqlalchemy
    import sqlalchemy


def _import_psycopg_libs():
    global psycopg2, execute_values
    import psycopg2
    from psycopg2.extras import execute_values


def _import_clickhouse_libs():
    global clickhouse_connect
    import clickhouse_connect


class SqlMedia(BaseMedia):
    """
    General SQL Media
    """
    def __init__(self, max_writers, **options):
        super().__init__(max_writers, **options)

        _import_sql_libs()

        if self._options.get("driver_execute"):
            # table_name should contain fields order like 'tb (a, b, c)'
            self.table = self._options["table_name"]
            self.table_params = re.findall(r"[^\s\(\),]+", self.table)
            tmp_fields = ",".join([f"%({par})s"
                                   for par in self.table_params[1:]])
            self.template_query = \
                f"INSERT INTO {self.table} VALUES ({tmp_fields})"
        else:
            self.table_params = re.findall(
                r"[^\s\(\),]+", self._options["table_name"])
            self.table = sqlalchemy.table(
                self.table_params[0],
                *[sqlalchemy.column(x) for x in self.table_params[1:]])

        self.con = None

    def _connect(self):
        self.engine = sqlalchemy.create_engine(self._options['dsn'])
        self.con = self.engine.connect()
        self.con.execution_options(autocommit=self._options["autocommit"])

    def _write(self, batch):
        # lazy connect to avoid multi-processing problems on connection
        if not self.con:
            self._connect()

        if self._options.get("driver_execute"):
            self.con.exec_driver_sql(self.template_query, batch)
        else:
            self.con.execute(self.table.insert(), batch)

    def __del__(self):
        if self.con:
            self.con.close()


class PsycopgMedia(SqlMedia):
    """
    Psycopg2 Media
    """
    def __init__(self, max_writers, **options):
        super().__init__(max_writers, **options)

        _import_psycopg_libs()

        self.template_query = f"INSERT INTO {self.table} VALUES %s"

    def _connect(self):
        self.con = psycopg2.connect(self._options['dsn'])
        self.curser = self.con.cursor()

    def _write(self, batch):
        # lazy connect to avoid multi-processing problems on connection
        if not self.con:
            self._connect()
        values = [[value for value in instance.values()] for instance in batch]
        execute_values(self.curser, self.template_query, values)
        self.con.commit()

    def __del__(self):
        if self.con:
            self.con.commit()
            self.con.close()


class ClickHouseMedia(SqlMedia):
    """
    Clickhouse Media
    """
    def __init__(self, max_writers, **options):
        super().__init__(max_writers, **options)

        _import_clickhouse_libs()

    def _connect(self):
        dsn = self._options["dsn"]
        if isinstance(dsn, str):
            dsn = dict(tuple(i.split("=", 1) + [""])[:2]
                       for i in dsn.split())
            dsn = {key: str(ast.literal_eval(value))
                   for key, value in dsn.items()}

        self.con = clickhouse_connect.get_client(**dsn)

    def _write(self, batch):
        if not self.con:
            self._connect()
        values = [[value for value in instance.values()] for instance in batch]
        self.con.insert(
            self.table_params[0], values, column_names=self.table_params[1:])
