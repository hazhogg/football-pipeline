# Premier League Football Data Pipeline

An automated data engineering pipeline that fetches live Premier League data and stores it in PostgreSQL for analysis and visualisation.

## What it does

- Fetches live standings, match results and top scorers from football-data.org API
- Stores all data in PostgreSQL for historical analysis
- Auto-updates scores 4 times daily (8am, 6pm, 10pm, midnight)
- Detects and flags new results since last run
- Generates 6 visualisation charts
- Runs automatically in Docker

## Tech stack

- Python
- pandas
- PostgreSQL
- psycopg2
- football-data.org API
- schedule
- matplotlib
- Docker

## Data collected

### standings
Live Premier League table updated after every matchday:

| Column | Description |
|---|---|
| position | League position |
| team | Team name |
| played | Matches played |
| won / drawn / lost | Results breakdown |
| goals_for / goals_against | Goals stats |
| goal_diff | Goal difference |
| points | Total points |

### matches
All 380 Premier League fixtures with live scores:

| Column | Description |
|---|---|
| match_id | Unique match identifier |
| match_date | Kickoff date and time |
| home_team / away_team | Teams |
| home_score / away_score | Final scores |
| status | TIMED / FINISHED |
| matchday | Matchday number (1-38) |

### top_scorers
Live Golden Boot standings:

| Column | Description |
|---|---|
| player | Player name |
| team | Club |
| goals | Goals scored |
| assists | Assists |
| penalties | Penalties scored |

## Setup

### Option 1 — Docker (recommended)

1. Get a free API key at https://www.football-data.org/client/register

2. Clone the repo:
```bash
git clone https://github.com/yourusername/football-pipeline.git
cd football-pipeline
```

3. Create a `.env` file:
```
DB_PASSWORD=yourpassword
DB_HOST=db
FOOTBALL_API_KEY=your_api_key
```

4. Run:
```bash
docker compose up --build
```

### Option 2 — Local

1. Install PostgreSQL and create a database:
```bash
python create_db.py
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```
DB_PASSWORD=yourpassword
DB_HOST=localhost
FOOTBALL_API_KEY=your_api_key
```

4. Run:
```bash
python football_pipeline.py
```

## Visualisations

Run after pipeline has collected data:
```bash
python visualise.py
```

Generates 6 charts:
- Premier League standings
- Goals scored vs conceded
- Wins, draws and losses
- Season progress by matchday
- Top scorers and assists
- Latest match results

## Example queries

```sql
-- Current top 5
SELECT position, team, played, points
FROM standings
WHERE fetched_at >= (SELECT MAX(fetched_at) - INTERVAL '1 minute' FROM standings)
ORDER BY position
LIMIT 5;

-- This week's fixtures
SELECT home_team, away_team, match_date
FROM matches
WHERE match_date BETWEEN NOW() AND NOW() + INTERVAL '7 days'
ORDER BY match_date;

-- Results checker — new results since last run
SELECT home_team, home_score, away_score, away_team
FROM matches
WHERE status = 'FINISHED'
ORDER BY match_date DESC
LIMIT 10;
```

## Project structure

```
football-pipeline/
├── football_pipeline.py  ← main ETL pipeline
├── visualise.py          ← chart generation
├── analyse.py            ← SQL analysis queries
├── create_db.py          ← database setup
├── requirements.txt      ← dependencies
├── Dockerfile            ← Docker configuration
├── docker-compose.yml    ← multi-container setup
├── .gitignore            ← excludes .env and cache
└── .env                  ← API key and DB password (not pushed)
```

## Schedule

Pipeline runs automatically:
```
08:00  → morning update
18:00  → pre-evening kickoffs
22:00  → post-match results
00:00  → final results
```

## Author

Harry
