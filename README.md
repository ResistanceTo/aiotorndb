[torndb](https://github.com/bdarnell/torndb) rewrite to asynchronous

## Example

First get a connection object

```python
from aiotorndb import Connection

conn = Connection(
    host="127.0.0.1",
    db="test",
    user="root",
    password="123456",
    port=3306,
    time_zone="+8:00",
    charset="utf8",
)
```

Next, you can use methods such as select, update, insert, delete, etc.

```python
import asyncio

async def test():
    get_result = await conn.get("select * from user where id = 1")
    print(get_result)
    # {'id': 1, 'name': 'tom'}

    select_result = await conn.select("select * from user")
    print(select_result)
    # [{'id': 1, 'name': 'tom'}, {'id': 2, 'name': 'ellis'}]

    update_result = await conn.update("update user set name = %(name)s where id = 1", name="eddie")
    print(update_result)
    # 1

    insert_result = await conn.insert("insert into user (name) values (%(name)s)", name="dav")
    print(insert_result)
    # 3

    # sql = select * from user where id in (1, 3)
    select_result2 = await conn.select("select * from user where id in %(user_ids)s", user_ids=[1, 3])
    print(select_result2)
    # [{'id': 1, 'name': 'eddie'}, {'id': 3, 'name': 'dav'}]

    # sql = select * from project_tag where name like '%e%'
    select_result3 = await conn.select("select * from project_tag where name like %(name)s", name="%e%")
    print(select_result3)
    # [{'id': 1, 'name': 'eddie'}, {'id': 2, 'name': 'ellis'}]

asyncio.run(test())
```
