import mysql.connector
from flask import current_app
from config import Config

def get_db():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST, port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER, password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE, charset="utf8mb4",
        collation="utf8mb4_unicode_ci"
    )

def init_db():
    import os
    conn = mysql.connector.connect(host=Config.MYSQL_HOST, port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER, password=Config.MYSQL_PASSWORD)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.close(); conn.close()
    conn = get_db()
    cur = conn.cursor()
    schema = os.path.join(os.path.dirname(__file__), "database", "schema.sql")
    with open(schema, encoding="utf-8") as f:
        statements = [s.strip() for s in f.read().split(";") if s.strip()]
    for statement in statements:
        cur.execute(statement)
    conn.commit()
    seed = os.path.join(os.path.dirname(__file__), "database", "seed.sql")
    with open(seed, encoding="utf-8") as f:
        statements = [s.strip() for s in f.read().split(";") if s.strip()]
    for statement in statements:
        cur.execute(statement)
    conn.commit()
    cur.close(); conn.close()
