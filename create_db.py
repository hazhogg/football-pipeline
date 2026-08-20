import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to default postgres database first
conn = psycopg2.connect(
    host='localhost',
    database='postgres',
    user='postgres',
    password=os.environ.get('DB_PASSWORD'),
    port='5432'
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()
cursor.execute('CREATE DATABASE football_db')
conn.close()
print('football_db created!')