import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host='localhost',
    database='football_db',
    user='postgres',
    password=os.environ.get('DB_PASSWORD'),
    port='5432'
)

# How many matches are scheduled?
print('--- Season Schedule ---')
result = pd.read_sql("""
    SELECT status, COUNT(*) as count
    FROM matches
    GROUP BY status
    ORDER BY count DESC
""", conn)
print(result)

# First matchday fixtures
print('\n--- Matchday 1 Fixtures ---')
result = pd.read_sql("""
    SELECT home_team, away_team, match_date, status
    FROM matches
    WHERE matchday = 1
    ORDER BY match_date
""", conn)
print(result.to_string(index=False))

# This week's fixtures
print('\n--- This Week fixtures ---')
result = pd.read_sql("""
    SELECT home_team, away_team,
           TO_CHAR(match_date, 'Dy DD Mon HH24:MI') as kickoff
    FROM matches
    WHERE match_date BETWEEN NOW() AND NOW() + INTERVAL '7 days'
    ORDER BY match_date
""", conn)
print(result.to_string(index=False))

# Total matches per matchday
print('\n--- Matches per Matchday ---')
result = pd.read_sql("""
    SELECT matchday, COUNT(*) as matches,
           SUM(CASE WHEN status = 'FINISHED' THEN 1 ELSE 0 END) as played
    FROM matches
    GROUP BY matchday
    ORDER BY matchday
    LIMIT 5
""", conn)
print(result.to_string(index=False))

conn.close()