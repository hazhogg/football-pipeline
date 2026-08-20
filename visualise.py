import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
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

# ── 1. STANDINGS BAR CHART ─────────────────────────────────────────────────
def plot_standings():
    df = pd.read_sql("""
        SELECT position, team, points, won, drawn, lost, goals_for, goals_against
        FROM standings
        WHERE fetched_at >= (SELECT MAX(fetched_at) - INTERVAL '1 minute' FROM standings)
        ORDER BY position
    """, conn)

    df['team'] = df['team'].str.replace(' FC', '').str.replace(' AFC', '')

    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.barh(df['team'][::-1], df['points'][::-1], color='#5b4fcf')
    ax.set_xlabel('Points')
    ax.set_title('Premier League Standings', fontsize=16, fontweight='bold')
    ax.bar_label(bars, padding=3)
    plt.tight_layout()
    plt.savefig('standings.png', dpi=150)
    plt.show()
    print('Saved standings.png')

# ── 2. GOALS SCORED vs CONCEDED ────────────────────────────────────────────
def plot_goals():
    df = pd.read_sql("""
        SELECT team, goals_for, goals_against, goal_diff
        FROM standings
        WHERE fetched_at >= (SELECT MAX(fetched_at) - INTERVAL '1 minute' FROM standings)
        ORDER BY goals_for DESC
        LIMIT 10
    """, conn)

    df['team'] = df['team'].str.replace(' FC', '').str.replace(' AFC', '')

    x = range(len(df))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar([i - width/2 for i in x], df['goals_for'],     width, label='Goals For',     color='#22c55e')
    ax.bar([i + width/2 for i in x], df['goals_against'], width, label='Goals Against', color='#ef4444')
    ax.set_xticks(x)
    ax.set_xticklabels(df['team'], rotation=45, ha='right')
    ax.set_ylabel('Goals')
    ax.set_title('Goals Scored vs Conceded (Top 10)', fontsize=16, fontweight='bold')
    ax.legend()
    plt.tight_layout()
    plt.savefig('goals.png', dpi=150)
    plt.show()
    print('Saved goals.png')

# ── 3. WINS / DRAWS / LOSSES ───────────────────────────────────────────────
def plot_results():
    df = pd.read_sql("""
        SELECT team, won, drawn, lost
        FROM standings
        WHERE fetched_at >= (SELECT MAX(fetched_at) - INTERVAL '1 minute' FROM standings)
        ORDER BY won DESC
        LIMIT 10
    """, conn)

    df['team'] = df['team'].str.replace(' FC', '').str.replace(' AFC', '')

    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(df))
    width = 0.25

    ax.bar([i - width for i in x], df['won'],   width, label='Won',   color='#22c55e')
    ax.bar([i         for i in x], df['drawn'], width, label='Drawn', color='#f59e0b')
    ax.bar([i + width for i in x], df['lost'],  width, label='Lost',  color='#ef4444')
    ax.set_xticks(x)
    ax.set_xticklabels(df['team'], rotation=45, ha='right')
    ax.set_ylabel('Matches')
    ax.set_title('Wins, Draws and Losses (Top 10)', fontsize=16, fontweight='bold')
    ax.legend()
    plt.tight_layout()
    plt.savefig('results.png', dpi=150)
    plt.show()
    print('Saved results.png')

# ── 4. SEASON PROGRESS BY MATCHDAY ────────────────────────────────────────
def plot_matchdays():
    df = pd.read_sql("""
        SELECT matchday,
               COUNT(*) as total,
               SUM(CASE WHEN status = 'FINISHED' THEN 1 ELSE 0 END) as played
        FROM matches
        GROUP BY matchday
        ORDER BY matchday
    """, conn)

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.bar(df['matchday'], df['total'],  color='#e0e7ff', label='Scheduled')
    ax.bar(df['matchday'], df['played'], color='#5b4fcf', label='Played')
    ax.set_xlabel('Matchday')
    ax.set_ylabel('Matches')
    ax.set_title('Season Progress by Matchday', fontsize=16, fontweight='bold')
    ax.legend()
    plt.tight_layout()
    plt.savefig('matchdays.png', dpi=150)
    plt.show()
    print('Saved matchdays.png')

# ── 5. TOP SCORERS ─────────────────────────────────────────────────────────
def plot_scorers():
    df = pd.read_sql("""
        SELECT player, team, goals, assists
        FROM top_scorers
        WHERE fetched_at >= (SELECT MAX(fetched_at) - INTERVAL '1 minute' FROM top_scorers)
        ORDER BY goals DESC
        LIMIT 10
    """, conn)

    if len(df) == 0:
        print('No scorers yet — waiting for first matches!')
        return

    df['team'] = df['team'].str.replace(' FC', '').str.replace(' AFC', '')
    labels = [f"{row['player']}\n({row['team']})" for _, row in df.iterrows()]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(df))
    width = 0.35
    ax.bar([i - width/2 for i in x], df['goals'],   width, label='Goals',   color='#5b4fcf')
    ax.bar([i + width/2 for i in x], df['assists'], width, label='Assists', color='#a78bfa')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_ylabel('Count')
    ax.set_title('Top Scorers and Assists', fontsize=16, fontweight='bold')
    ax.legend()
    plt.tight_layout()
    plt.savefig('scorers.png', dpi=150)
    plt.show()
    print('Saved scorers.png')

# ── 6. LATEST RESULTS ──────────────────────────────────────────────────────
def plot_latest_results():
    df = pd.read_sql("""
        SELECT home_team, home_score, away_score, away_team
        FROM matches
        WHERE status = 'FINISHED'
        ORDER BY match_date DESC
        LIMIT 10
    """, conn)

    if len(df) == 0:
        print('No results yet!')
        return

    df['home_team'] = df['home_team'].str.replace(' FC', '').str.replace(' AFC', '')
    df['away_team'] = df['away_team'].str.replace(' FC', '').str.replace(' AFC', '')
    df['label'] = df['home_team'] + ' vs ' + df['away_team']
    df['score'] = df['home_score'].astype(int).astype(str) + ' - ' + df['away_score'].astype(int).astype(str)

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = []
    for _, row in df.iterrows():
        if row['home_score'] > row['away_score']:
            colors.append('#22c55e')
        elif row['away_score'] > row['home_score']:
            colors.append('#ef4444')
        else:
            colors.append('#f59e0b')

    ax.barh(df['label'][::-1], [1]*len(df), color=colors[::-1])
    for i, (_, row) in enumerate(df[::-1].iterrows()):
        ax.text(0.5, i, row['score'], ha='center', va='center',
                fontsize=12, fontweight='bold', color='white')

    ax.set_xlim(0, 1)
    ax.set_xticks([])
    ax.set_title('Latest Results', fontsize=16, fontweight='bold')

    from matplotlib.patches import Patch
    legend = [
        Patch(color='#22c55e', label='Home Win'),
        Patch(color='#ef4444', label='Away Win'),
        Patch(color='#f59e0b', label='Draw'),
    ]
    ax.legend(handles=legend, loc='lower right')
    plt.tight_layout()
    plt.savefig('latest_results.png', dpi=150)
    plt.show()
    print('Saved latest_results.png')

# ── RUN ALL ────────────────────────────────────────────────────────────────
print('Generating visualisations...')
plot_standings()
plot_goals()
plot_results()
plot_matchdays()
plot_scorers()
plot_latest_results()

conn.close()
print('\nAll charts saved!')