"""
PostgreSQL: asyncpg
MySQL: aiomysql
"""
import asyncio
import asyncpg
from asyncpg import Record
from typing import List

from faker import Faker


CREATE_BRAND_SQL = """
    CREATE TABLE IF NOT EXISTS brand(
        brand_id SERIAL PRIMARY KEY,
        brand_name TEXT NOT NULL
    );
"""

CREATE_PRODUCT_TABLE_SQL = """
    CREATE TABLE product 
    (
        product_id SERIAL PRIMARY KEY,
        product_name TEXT NOT NULL,
        brand_id INT NOT NULL,
        FOREIGN KEY (brand_id) REFERENCES brand(brand_id)
    );
"""

CREATE_PRODUCT_COLOR_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS product_color(
        product_color_id SERIAL PRIMARY KEY,
        product_color_name TEXT NOT NULL
   );
"""

CREATE_PRODUCT_SIZE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS product_size(
        product_size_id SERIAL PRIMARY KEY,
        product_size_name TEXT NOT NULL
    );
"""

CREATE_PRODUCT_SIZE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS product_size (
        product_size_id SERIAL PRIMARY KEY,
        product_size_name TEXT NOT NULL
    );
"""

CREATE_SKU_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS sku(
        sku_id SERIAL PRIMARY KEY,
        product_id INT NOT NULL,
        product_size_id INT NOT NULL,
        product_color_id INT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES product(product_id),
        FOREIGN KEY(product_size_id) REFERENCES product_size(product_size_id),
        FOREIGN KEY(product_color_id) REFERENCES product_color(product_color_id)
    );
"""

COLOR_INSERT_SQL = """
    INSERT INTO product_color VALUES(1, 'Blue');
    INSERT INTO product_color VALUES(2, 'Black');
"""

SIZE_INSERT_SQL = """
    INSERT INTO product_size VALUES(1, 'Small');
    INSERT INTO product_size VALUES(2, 'Medium');
    INSERT INTO product_size VALUES(3, 'Large');
"""


async def insert_brands(conn):
    f = Faker(locale=['en_US'])
    results: List[Record] = await conn.fetch('SELECT brand_id, brand_name FROM brand')
    brand_set = {r['brand_name'] for r in results}

    brands = []
    max_times = 1000

    while 1:
        brand_name1 = f.first_name()
        brand_name2 = f.last_name()
        print(f'brands Cnt: {len(brands)}, {brand_name1}, {brand_name2}')

        if brand_name1 not in brand_set:
            brands.append((brand_name1, ))

        if brand_name2 not in brand_set:
            brands.append((brand_name2, ))

        brand_set.add(brand_name1)
        brand_set.add(brand_name2)

        if len(brands) > max_times:
            break

    return await conn.executemany(
        "INSERT INTO brand VALUES (DEFAULT, $1)",
        brands
    )


async def main():
    connection = await asyncpg.connect(
        host='127.0.0.1',
        port=5432,
        database='fosunlinkdb',
        user='fosunlink',
        password='fosunlink123Ab'
    )

    version = connection.get_server_version()
    print(f'Connected Postgres is {version}')
    print(f'get_settings is {connection.get_settings()}')

    sql_dict = {k: v for k, v in globals().items() if k.isupper() and k.endswith('_SQL')}

    # await insert_brands(connection)

    rows = await connection.fetchval('SELECT COUNT(1) FROM brand')
    print(f'Brand rows: {rows}')

    await connection.close()


if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

