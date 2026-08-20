import requests
import pandas as pd
import psycopg2
import os
import schedule
import time
import warnings
from datetime import datetime
from dotenv import load_dotenv

warnings.filterwarnings('ignore')
load_dotenv()

# ── CONFIG ─────────────────────────────────────────────────────────────────
API_KEY = os.environ.get('FOOTBALL_API_KEY')
HEADERS = {'X-Auth-Token': API_KEY}
BASE_URL = 'https://api.football-data.org/v4'

DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', 'localhost'),
    'database': 'football_db',
    'user':     'postgres',
    'password': os.environ.get('DB_PASSWORD'),
    'port':     '5432'
}

# ── SETUP DATABASE ─────────────────────────────────────────────────────────
def setup_database(conn):
    cursor = conn.cursor()

    # Standings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS standings (
            id         SERIAL PRIMARY KEY,
            fetched_at TIMESTAMP,
            position   INTEGER,
            team       VARCHAR(100),
            played     INTEGER,
            won        INTEGER,
            drawn      INTEGER,
            lost       INTEGER,
            goals_for  INTEGER,
            goals_against INTEGER,
            goal_diff  INTEGER,
            points     INTEGER
        )
    """)

    # Matches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id            SERIAL PRIMARY KEY,
            match_id      INTEGER UNIQUE,
            match_date    TIMESTAMP,
            home_team     VARCHAR(100),
            away_team     VARCHAR(100),
            home_score    INTEGER,
            away_score    INTEGER,
            status        VARCHAR(50),
            matchday      INTEGER,
            fetched_at    TIMESTAMP
        )
    """)

    # Top scorers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS top_scorers (
            id         SERIAL PRIMARY KEY,
            fetched_at TIMESTAMP,
            player     VARCHAR(100),
            team       VARCHAR(100),
            goals      INTEGER,
            assists    INTEGER,
            penalties  INTEGER
        )
    """)

    conn.commit()
    print('Database ready!')

# ── EXTRACT ────────────────────────────────────────────────────────────────
def extract_standings():
    print('  Extracting standings...')
    response = requests.get(f'{BASE_URL}/competitions/PL/standings', headers=HEADERS)
    if response.status_code != 200:
        raise Exception(f'API error: {response.status_code}')
    return response.json()

def extract_matches():
    print('  Extracting matches...')
    response = requests.get(f'{BASE_URL}/competitions/PL/matches', headers=HEADERS)
    if response.status_code != 200:
        raise Exception(f'API error: {response.status_code}')
    return response.json()

def extract_scorers():
    print('  Extracting top scorers...')
    response = requests.get(f'{BASE_URL}/competitions/PL/scorers', headers=HEADERS)
    if response.status_code != 200:
        raise Exception(f'API error: {response.status_code}')
    return response.json()

# ── TRANSFORM ──────────────────────────────────────────────────────────────
def transform_standings(data):
    print('  Transforming standings...')
    rows = []
    for team in data['standings'][0]['table']:
        rows.append({
            'fetched_at':    datetime.now(),
            'position':      team['position'],
            'team':          team['team']['name'],
            'played':        team['playedGames'],
            'won':           team['won'],
            'drawn':         team['draw'],
            'lost':          team['lost'],
            'goals_for':     team['goalsFor'],
            'goals_against': team['goalsAgainst'],
            'goal_diff':     team['goalDifference'],
            'points':        team['points'],
        })
    return pd.DataFrame(rows)

def transform_matches(data):
    print('  Transforming matches...')
    rows = []
    for match in data['matches']:
        home = match['score']['fullTime']['home']
        away = match['score']['fullTime']['away']
        rows.append({
            'match_id':   match['id'],
            'match_date': match['utcDate'],
            'home_team':  match['homeTeam']['name'],
            'away_team':  match['awayTeam']['name'],
            'home_score': home,
            'away_score': away,
            'status':     match['status'],
            'matchday':   match['matchday'],
            'fetched_at': datetime.now(),
        })
    return pd.DataFrame(rows)

def transform_scorers(data):
    print('  Transforming scorers...')
    rows = []
    for entry in data['scorers']:
        rows.append({
            'fetched_at': datetime.now(),
            'player':     entry['player']['name'],
            'team':       entry['team']['name'],
            'goals':      entry['goals'],
            'assists':    entry.get('assists') or 0,
            'penalties':  entry.get('penalties') or 0,
        })
    return pd.DataFrame(rows)

# ── LOAD ───────────────────────────────────────────────────────────────────
def load_standings(df, conn):
    print(f'  Loading {len(df)} standings rows...')
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO standings
            (fetched_at, position, team, played, won, drawn, lost,
             goals_for, goals_against, goal_diff, points)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, tuple(row))
    conn.commit()

def load_matches(df, conn):
    print(f'  Loading {len(df)} matches...')
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO matches
            (match_id, match_date, home_team, away_team, home_score,
             away_score, status, matchday, fetched_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (match_id) DO UPDATE SET
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score,
                status     = EXCLUDED.status,
                fetched_at = EXCLUDED.fetched_at
        """, tuple(row))
    conn.commit()

def load_scorers(df, conn):
    print(f'  Loading {len(df)} scorers...')
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO top_scorers
            (fetched_at, player, team, goals, assists, penalties)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, tuple(row))
    conn.commit()

# ── MAIN PIPELINE ──────────────────────────────────────────────────────────
def run_pipeline():
    print(f'\n[{datetime.now().strftime("%H:%M:%S")}] Running football pipeline...')
    try:
        conn = psycopg2.connect(**DB_CONFIG)

        # Standings
        print('\nStandings:')
        standings_raw = extract_standings()
        standings_df  = transform_standings(standings_raw)
        load_standings(standings_df, conn)

        # Matches
        print('\nMatches:')
        matches_raw = extract_matches()
        matches_df  = transform_matches(matches_raw)
        load_matches(matches_df, conn)

        # Top Scorers
        print('\nTop Scorers:')
        scorers_raw = extract_scorers()
        scorers_df  = transform_scorers(scorers_raw)
        load_scorers(scorers_df, conn)

        print(f'\n✅ Pipeline complete!')

                # Quick summary
        print('\n--- Pipeline Summary ---')
        summary = pd.read_sql("""
            SELECT
                status,
                COUNT(*) as matches,
                SUM(CASE WHEN status = 'FINISHED' THEN home_score + away_score ELSE 0 END) as total_goals
            FROM matches
            GROUP BY status
            ORDER BY status
        """, conn)
        print(summary.to_string(index=False))

        # Latest results
        print('\n--- Latest Results ---')
        results = pd.read_sql("""
            SELECT home_team, home_score, away_score, away_team,
                TO_CHAR(match_date, 'DD Mon') as date
            FROM matches
            WHERE status = 'FINISHED'
            ORDER BY match_date DESC
            LIMIT 10
        """, conn)
        if len(results) > 0:
            print(results.to_string(index=False))
        else:
            print('No results yet — season hasnt started!')

        # Current standings
        print('\n--- Current Standings (Top 10) ---')
        standings = pd.read_sql("""
            SELECT position, team, played, won, drawn, lost,
                goals_for, goals_against, goal_diff, points
            FROM standings
            WHERE fetched_at = (SELECT MAX(fetched_at) FROM standings)
            ORDER BY position
            LIMIT 10
        """, conn)
        print(standings.to_string(index=False))

        # Check for new results
        print('\nChecking for new results...')
        check_new_results(conn)

        conn.close()  # ← this stays last

    except Exception as e:
        print(f'❌ Pipeline failed: {e}')

    # ── RESULT CHECKER ─────────────────────────────────────────────────────────
def check_new_results(conn):
    """Compare latest fetch with previous fetch to find new results"""
    
    # Get the two most recent fetch times
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT fetched_at 
        FROM matches 
        ORDER BY fetched_at DESC 
        LIMIT 2
    """)
    fetch_times = cursor.fetchall()
    
    if len(fetch_times) < 2:
        print('  Not enough data yet to compare — need at least 2 runs')
        return
    
    latest = fetch_times[0][0]
    previous = fetch_times[1][0]
    
    # Find matches that changed status to FINISHED
    new_results = pd.read_sql("""
        SELECT 
            curr.home_team,
            curr.home_score,
            curr.away_score,
            curr.away_team,
            TO_CHAR(curr.match_date, 'DD Mon HH24:MI') as kickoff
        FROM matches curr
        JOIN matches prev ON curr.match_id = prev.match_id
        WHERE curr.fetched_at = %(latest)s
          AND prev.fetched_at = %(previous)s
          AND curr.status = 'FINISHED'
          AND prev.status != 'FINISHED'
        ORDER BY curr.match_date
    """, conn, params={'latest': latest, 'previous': previous})
    
    if len(new_results) > 0:
        print(f'\n🆕 New results since last run:')
        for _, match in new_results.iterrows():
            home = match['home_team'].replace(' FC', '').replace(' AFC', '')
            away = match['away_team'].replace(' FC', '').replace(' AFC', '')
            h_score = int(match['home_score'])
            a_score = int(match['away_score'])
            
            # Determine result
            if h_score > a_score:
                result = f'🏆 {home} WIN'
            elif a_score > h_score:
                result = f'🏆 {away} WIN'
            else:
                result = '🤝 DRAW'
                
            print(f'  {home} {h_score}-{a_score} {away} ({match["kickoff"]}) — {result}')
    else:
        print('\n  No new results since last run')
    
    # Find matches where score changed (in progress updates)
    score_changes = pd.read_sql("""
        SELECT 
            curr.home_team,
            curr.home_score,
            curr.away_score,
            curr.away_team,
            prev.home_score as prev_home,
            prev.away_score as prev_away
        FROM matches curr
        JOIN matches prev ON curr.match_id = prev.match_id
        WHERE curr.fetched_at = %(latest)s
          AND prev.fetched_at = %(previous)s
          AND curr.status = 'FINISHED'
          AND prev.status = 'FINISHED'
          AND (curr.home_score != prev.home_score 
           OR curr.away_score != prev.away_score)
    """, conn, params={'latest': latest, 'previous': previous})
    
    if len(score_changes) > 0:
        print(f'\n📝 Score corrections detected:')
        for _, match in score_changes.iterrows():
            home = match['home_team'].replace(' FC', '').replace(' AFC', '')
            away = match['away_team'].replace(' FC', '').replace(' AFC', '')
            print(f'  {home} vs {away}: {int(match["prev_home"])}-{int(match["prev_away"])} → {int(match["home_score"])}-{int(match["away_score"])}')

# ── RUN ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    conn = psycopg2.connect(**DB_CONFIG)
    setup_database(conn)
    conn.close()

    # Run immediately on start
    run_pipeline()

    # Smart schedule — covers all kickoff times
    schedule.every().day.at('08:00').do(run_pipeline)  # morning
    schedule.every().day.at('18:00').do(run_pipeline)  # pre-evening kickoffs
    schedule.every().day.at('22:00').do(run_pipeline)  # post-match
    schedule.every().day.at('00:00').do(run_pipeline)  # midnight final

    print('\nScheduler running — updates at 8am, 6pm, 10pm, midnight.')
    print('Press Ctrl+C to stop.\n')

    while True:
        schedule.run_pending()
        time.sleep(60)