"""
Simple import utility to create a SQLite DB from schema.sql and import CSV sample files.
Run from the project folder where `schema.sql` and CSV files exist.

Usage:
    python import_to_sqlite.py --db crm_base.db

After running, open LibreOffice Base and connect to `crm_base.db` ("Connect to an existing database" -> SQLite).
"""
import argparse
import csv
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser(description='Create SQLite DB and import CSVs for LibreOffice Base')
parser.add_argument('--db', default='crm_base.db', help='SQLite database file to create')
args = parser.parse_args()

BASE = Path(__file__).parent
SCHEMA = BASE / 'schema.sql'
DB = BASE / args.db

if not SCHEMA.exists():
    print('schema.sql not found in', BASE)
    raise SystemExit(1)

print('Creating DB:', DB)
sql_text = SCHEMA.read_text(encoding='utf-8')
with sqlite3.connect(str(DB)) as conn:
    conn.executescript(sql_text)
    conn.commit()

# Import CSVs if present (detect by *_brokers.csv etc.)
for csv_file in BASE.glob('*.csv'):
    name = csv_file.stem
    print('Importing', csv_file.name, 'into table', name)
    with csv_file.open(newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        rows = [row for row in reader]
        if not rows:
            continue
        cols = list(rows[0].keys())
        placeholders = ','.join(['?'] * len(cols))
        insert_sql = f"INSERT INTO {name} ({', '.join(cols)}) VALUES ({placeholders})"
        with sqlite3.connect(str(DB)) as conn:
            conn.executemany(insert_sql, ([row.get(col) for col in cols] for row in rows))
            conn.commit()

print('Done. Open LibreOffice Base and connect to:', DB)
