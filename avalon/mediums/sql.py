import re

from . import BaseMedia
from ..registry import RequiredValue
from ..auxiliary import key_values_str_to_dict, parse_db_url, classproperty


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


class BaseSqlMedia(BaseMedia):
    """
    Base for SQL Media
    """

    __title__ = "sql"
    args_group_description = "Arguments for all 'sql' based media"

    default_format = "sql"

    schemes = []

    def __init__(self, max_writers=None, **options):
        super().__init__(max_writers, **options)

        self.table_params = re.findall(r"[^\s\(\),]+",
                                       self.table_definition)

        self.con = None

    @classproperty
    def args_group_description(cls):
        return (
            "Arguments for all 'sql' based media"
            if cls.args_group_title and cls.args_list() and
            not cls.disable_args_group else None)

    @classmethod
    def add_arguments(cls, group):
        """
        Add class arguemtns to the argparse group
        """
        group.add_argument(
            "--sql-dsn", metavar="<DSN>", type=str,
            default=RequiredValue("--sql-dsn"),
            help="Determines database 'Data source name'. \
            This should be in form of \
            'dialect[+driver]://user:password@host/dbname'")
        group.add_argument(
            "--sql-table", metavar="<tbl>", type=str,
            default=RequiredValue("--sql-table"),
            dest="sql_table_definition",
            help="Determines database table name. \
            This name should contain fields order for exmaple 'tbl (a, b, c)'")

    @classmethod
    def check_args_namespace_relation(cls, args=None, namespace=None):
        """
        Returns a number that determines how strong the relation
        between the arguments and this class is.
        """
        if namespace and isinstance(getattr(namespace, "sql_dsn", None), str):
            scheme = parse_db_url(namespace.sql_dsn).get("scheme")
            if scheme in cls.schemes:
                return 100
            elif cls.schemes and scheme:
                # The class has defined a shcemes list, the user also
                # provided a scheme; but these two are different.
                return 0

        return super().check_args_namespace_relation(
            args=args, namespace=namespace)

    def _connect(self):
        pass

    def __del__(self):
        try:
            self.con.close()
        except Exception:
            pass


class SqlMedia(BaseSqlMedia):
    """
    SQL Media implemented with SQLAlchemy
    """

    __title__ = "sql"

    def __init__(self, max_writers=None, **options):
        super().__init__(max_writers, **options)

        _import_sql_libs()

        if self.driver_execute:
            # table_definition should contain fields order like
            # "tb (a, b, c)"
            self.table = self.table_definition
            tmp_fields = ",".join([f"%({par})s"
                                   for par in self.table_params[1:]])
            self.template_query = \
                f"INSERT INTO {self.table} VALUES ({tmp_fields})"
        else:
            self.table = sqlalchemy.table(
                self.table_params[0],
                *[sqlalchemy.column(x) for x in self.table_params[1:]])

    @classmethod
    def add_arguments(cls, group):
        """
        Add class arguemtns to the argparse group
        """
        super().add_arguments(group)

        group.add_argument(
            "--sql-autocommit", action="store_true",
            help="Enables query autocommit \
            (is not valid for psycopg media).")
        group.add_argument(
            "--sql-driver-execute", action="store_true",
            help="Enables sqlalchemy native driver execute to improve \
            performance.")

    def _connect(self):
        self.engine = sqlalchemy.create_engine(self.dsn)
        self.con = self.engine.connect()
        self.con.execution_options(autocommit=self.autocommit)

    def _write(self, batch):
        # lazy connect to avoid multi-processing problems on connection
        if not self.con:
            self._connect()

        if self.driver_execute:
            self.con.exec_driver_sql(self.template_query, batch)
        else:
            self.con.execute(self.table.insert(), batch)


class PsycopgMedia(BaseSqlMedia):
    """
    Psycopg2 Media
    """

    __title__ = "psycopg"

    # Only accept related arguments (and ignore other "sql_"
    # prefixed arguments such as "sql_autocommit")
    args_mapping = {"sql_dsn": "dsn",
                    "sql_table_definition": "table_definition"}

    # remove the 'psycopg' entry from cli help
    disable_args_group = True

    schemes = ["postgresql"]

    def __init__(self, max_writers=None, **options):
        super().__init__(max_writers, **options)

        _import_psycopg_libs()

        self.template_query = f"INSERT INTO {self.table_definition} VALUES %s"

    @classmethod
    def add_arguments(cls, group):
        """
        Add class arguemtns to the argparse group
        """
        # no new arguments other than the SqlMedia arguments is
        # required
        pass

    @classmethod
    def default_kwargs(cls):
        return {"dsn": RequiredValue("--sql-dsn"),
                "table_definition": RequiredValue("--sql-table")}

    def _connect(self):
        self.con = psycopg2.connect(self.dsn)
        self.curser = self.con.cursor()

    def _write(self, batch):
        # lazy connect to avoid multi-processing problems on connection
        if not self.con:
            self._connect()
        values = [[value for value in instance.values()] for instance in batch]
        execute_values(self.curser, self.template_query, values)
        self.con.commit()

    def __del__(self):
        try:
            self.con.commit()
        except Exception:
            pass

        super().__del__()


class ClickHouseMedia(SqlMedia):
    """
    Clickhouse Media
    """

    __title__ = "clickhouse"

    # All the arguments are just like SQLMedia with "sql_" prefix
    args_prefix = "sql_"

    # remove the 'clickhouse' entry from cli help
    disable_args_group = True

    schemes = ["clickhouse"]

    def __init__(self, max_writers=None, **options):
        super().__init__(max_writers, **options)

        _import_clickhouse_libs()

        dsn_url_dict = parse_db_url(self.dsn)
        self.dsn_dict = (dsn_url_dict if dsn_url_dict.pop("scheme", None)
                         else key_values_str_to_dict(self.dsn))

    @classmethod
    def add_arguments(cls, group):
        """
        Add class arguemtns to the argparse group
        """
        # no new arguments other than the SqlMedia arguments is
        # required
        pass

    @classmethod
    def default_kwargs(cls):
        """
        Returns a kwargs dictionary with default values to
        instantiate the class.
        """
        # Because the ClickHouseMedia `add_arguments` is overridden,
        # the `default_kwargs` has to also be overridden, otherwise it
        # will return an empty dictionary.

        # Use default values of SqlMedia
        return SqlMedia.default_kwargs()

    def _connect(self):
        self.con = clickhouse_connect.get_client(**self.dsn_dict)

    def _write(self, batch):
        if not self.con:
            self._connect()
        values = [[value for value in instance.values()] for instance in batch]
        self.con.insert(
            self.table_params[0], values, column_names=self.table_params[1:])
