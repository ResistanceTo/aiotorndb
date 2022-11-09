import aiomysql
import time
import copy

from pymysql.constants import FIELD_TYPE
from pymysql.constants import FLAG
from pymysql.converters import conversions


class Row(dict):
    """A dict that allows for object-like property access syntax."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


class Connection(object):
    def __init__(
        self,
        host,
        db,
        port=3306,
        user=None,
        password="",
        max_idle_time=7 * 3600,
        connect_timeout=10,
        time_zone="+0:00",
        charset="utf8",
        sql_mode="TRADITIONAL",
        autocommit=None,
    ) -> None:
        decoders = copy.copy(conversions)
        field_types = [FIELD_TYPE.BLOB, FIELD_TYPE.STRING, FIELD_TYPE.VAR_STRING]
        if "VARCHAR" in vars(FIELD_TYPE):
            field_types.append(FIELD_TYPE.VARCHAR)

        for field_type in field_types:
            decoders[field_type] = [(FLAG.BINARY, str)].append(decoders[field_type])  # type: ignore

        self.host = host
        self.max_idle_time = float(max_idle_time)
        args = dict(
            conv=decoders,
            host=host,
            user=user,
            password=password,
            db=db,
            charset=charset,
            init_command=('SET time_zone = "%s"' % time_zone),
            connect_timeout=connect_timeout,
            sql_mode=sql_mode,
            autocommit=autocommit,
            port=port,
        )

        if "/" in host:
            args["unix_socket"] = host

        self._db_args = args
        self._last_use_time = time.time()
        self._conn: aiomysql.Connection = None  # type: ignore
        # self._cur: aiomysql.Cursor = None  # type: ignore

    def __del__(self):
        try:
            self.close()
        except RuntimeError:
            pass

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None  # type: ignore

    async def reconnect(self):
        self.close()
        self._conn = await aiomysql.connect(**self._db_args)
        # self._cur = await self._conn.cursor()

    async def iter(self, query, *parameters, **kwparameters):
        """Returns an iterator for the given query and parameters."""
        await self._ensure_connected()
        cursor = aiomysql.cursors.SSCursor(self._conn)
        try:
            await cursor.execute(query, kwparameters or parameters)
            column_names = [d[0] for d in cursor.description]
            for row in cursor:
                yield Row(zip(column_names, row))
        except aiomysql.OperationalError:
            print("Error connecting to MySQL on %s", self.host)
            raise
        finally:
            await cursor.close()

    async def _ensure_connected(self):
        """Mysql by default closes client connections that are idle for
        8 hours, but the client library does not report this fact until
        you try to perform a query and it fails.  Protect against this
        case by preemptively closing and reopening the connection
        if it has been idle for too long (7 hours by default).
        """
        if self._conn is None or (
            time.time() - self._last_use_time > self.max_idle_time
        ):
            await self.reconnect()
        self._last_use_time = time.time()

    async def _cursor(self) -> aiomysql.Cursor:
        """Get an asynchronous cursor

        Returns:
            aiomysql.Cursor
        """
        await self._ensure_connected()
        return await self._conn.cursor()

    async def get(self, query, *parameters, **kwparameters):
        """Returns the (singular) row returned by the given query.
        If the query has no results, returns None.  If it has
        more than one result, raises an exception.
        """
        cursor = await self.__execute(query, *parameters, **kwparameters)
        if cursor.rowcount == 0:
            return None
        elif cursor.rowcount == 1:
            column_names = [d[0] for d in cursor.description]
            return [Row(zip(column_names, row)) for row in cursor._rows][0]
        else:
            raise Exception("Multiple rows returned for Database.get() query")

    async def select(self, query, *parameters, **kwparameters):
        cursor = await self.__execute(query, *parameters, **kwparameters)
        return self.__query_data(cursor)

    async def update(self, query, *parameters, **kwparameters):
        cursor = await self.__execute(query, *parameters, **kwparameters)
        return cursor.rowcount

    async def insert(self, query, *parameters, **kwparameters):
        cursor = await self.__execute(query, *parameters, **kwparameters)
        return cursor.lastrowid

    async def delete(self, query, *parameters, **kwparameters):
        cursor = await self.__execute(query, *parameters, **kwparameters)
        return cursor.rowcount

    async def __execute(self, query, *parameters, **kwparameters):
        """Executes the given query."""
        cursor = await self._cursor()
        try:
            await cursor.execute(query, kwparameters or parameters)
            return cursor
        except aiomysql.OperationalError:
            print("Error connecting to MySQL on %s", self.host)
            raise
        finally:
            await cursor.close()

    def __query_data(self, cursor):
        """Return the result set of the query.

        Returns:
            [{"id": 1, "name": "tom"}, {"id": 2, "name": "dav"}, ...]
        """
        column_names = [d[0] for d in cursor.description]
        return [Row(zip(column_names, row)) for row in cursor._rows]

    async def updatemany(self, query, parameters):
        """Executes the given query against all the given param sequences.
        We return the rowcount from the query.
        """
        cursor = await self.__executemany(query, parameters)
        return cursor.rowcount

    async def insertmany(self, query, parameters):
        """Executes the given query against all the given param sequences.
        We return the lastrowid from the query.
        """
        cursor = await self.__executemany(query, parameters)
        return cursor.lastrowid

    async def __executemany(self, query, parameters):
        cursor = await self._cursor()
        try:
            await cursor.executemany(query, parameters)
            return cursor
        finally:
            await cursor.close()
