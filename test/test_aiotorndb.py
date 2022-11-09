import sys

sys.path.append("../")

import asyncio
from aiotorndb import Connection


def connect_mysql(**kwargs):
    db = Connection(
        host=kwargs.get("host", "127.0.0.1"),
        db=kwargs.get("db"),
        user=kwargs.get("user"),
        password=kwargs.get("password", ""),
        port=kwargs.get("port", 3306),
        time_zone="+8:00",
        charset="utf8",
    )
    return db


db = connect_mysql(host="127.0.0.1", db="test", user="root", password="123456")


async def test():
    get = await db.get("select * from project_tag where id = 1")
    print(f"get: res = {get}")

    print("=" * 32)

    select = await db.select("select * from project_tag")
    print(f"select: res = {select}")

    print("=" * 32)

    update = await db.update(
        "update project_tag set name = %(tom)s where id = 1", tom="tom"
    )
    print(f"update: res = {update}")

    print("=" * 32)

    insert = await db.insert(
        "insert into project_tag (name) values (%(name)s)", name="dav"
    )
    print(f"insert: res = {insert}")


asyncio.run(test())
